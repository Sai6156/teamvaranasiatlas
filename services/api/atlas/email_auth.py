"""Supabase creates/verifies OTPs; Brevo only delivers them."""

import hashlib
import hmac
from typing import Literal
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from .config import settings
from .db import Database
from .email_delivery import require_email_delivery, send_code

router = APIRouter()


class CodeRequest(BaseModel):
    email: str = Field(
        min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    purpose: Literal["signup", "recovery"]
    password: str | None = Field(
        default=None, min_length=12, max_length=128, repr=False
    )
    full_name: str = Field(default="", max_length=100)


async def reserve_email(recipient: str, actor: str, scope: str = "auth"):
    config = settings()

    def digest(value):
        return hmac.new(
            config.supabase_service_role_key.encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    allowed = await Database(privileged=True).rpc(
        "reserve_auth_email",
        {
            "recipient_key": digest(scope + ":email:" + recipient.lower().strip()),
            "actor_key": digest(scope + ":actor:" + actor),
        },
    )
    if not allowed:
        raise HTTPException(
            429, "Please wait before requesting another email. Try again in a minute."
        )


@router.post("/auth/email-code", status_code=202)
async def request_code(body: CodeRequest, request: Request):
    require_email_delivery()
    if body.purpose == "signup" and not body.password:
        raise HTTPException(422, "Choose a password with at least 12 characters.")
    email = body.email.strip().lower()
    await reserve_email(email, request.client.host if request.client else "unknown")
    payload = {"type": body.purpose, "email": email}
    if body.purpose == "signup":
        payload.update(password=body.password, data={"full_name": body.full_name})
    db = Database(privileged=True)
    # Use the Auth admin endpoint only to create its native, single-use OTP.
    # Neither the OTP nor its hash is returned to the browser.
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            db.base + "/auth/v1/admin/generate_link", headers=db.headers, json=payload
        )
    if response.is_error:
        error_code = response.json().get("error_code", response.json().get("code"))
        if error_code not in ("email_exists", "user_not_found"):
            raise HTTPException(
                503,
                "Account verification is temporarily unavailable. Please try again.",
            )
    else:
        code = response.json().get("email_otp")
        if not code:
            raise HTTPException(
                503,
                "Account verification is temporarily unavailable. Please try again.",
            )
        await send_code(email, code, body.purpose)
    return {
        "message": "If this email is eligible, a verification code is on its way.",
        "resend_after_seconds": 60,
    }
