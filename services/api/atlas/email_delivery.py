"""Server-only transactional delivery. Never log email bodies or credentials."""

from html import escape
import httpx
from fastapi import HTTPException
from .config import settings


def require_email_delivery():
    config = settings()
    if not config.brevo_api_key or not config.brevo_sender_email:
        raise HTTPException(
            503, "Email delivery is being configured. Please try again shortly."
        )


async def send_email(recipient: str, subject: str, body: str):
    require_email_delivery()
    config = settings()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": config.brevo_api_key},
            json={
                "sender": {
                    "name": config.brevo_sender_name,
                    "email": config.brevo_sender_email,
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#24352b;padding:32px"><h1 style="color:#487b52">atlas.</h1>'
                + body
                + '<p style="font-size:12px;color:#68746d">Atlas · Company knowledge, connected</p></div>',
                "tags": ["atlas-transactional"],
            },
        )
    if response.is_error:
        raise HTTPException(
            503, "The email could not be sent. Please try again shortly."
        )
    return response.json().get("messageId")


async def send_code(recipient: str, code: str, purpose: str):
    title = "Verify your email" if purpose == "signup" else "Reset your password"
    return await send_email(
        recipient,
        f"{code} — Atlas {title.lower()}",
        f'<h2>{title}</h2><p>Enter this one-time code in Atlas:</p><p style="font-size:32px;font-weight:bold;letter-spacing:6px;background:#edf3eb;padding:20px;text-align:center">{escape(code)}</p><p>Use the latest code you requested. Never share it with anyone.</p><p>If you did not request this, you can ignore this email.</p>',
    )


async def send_invitation(recipient: str, workspace: str, url: str):
    return await send_email(
        recipient,
        f"You're invited to {workspace} on Atlas",
        f'<h2>Join {escape(workspace)}</h2><p>Your teammate invited you to their private company workspace.</p><p><a style="background:#487b52;color:white;padding:14px 22px;display:inline-block;text-decoration:none;border-radius:8px" href="{escape(url, quote=True)}">Accept invitation</a></p><p>Sign in with {escape(recipient)}, or create an account and verify your email with a code. Then accept your invitation.</p><p>This invitation expires in seven days and works only with the invited email address.</p>',
    )
