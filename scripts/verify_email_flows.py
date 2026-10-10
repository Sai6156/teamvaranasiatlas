"""Real Supabase auth/invitation regression; outbound email is captured locally.

This proves code and access behavior, not Brevo inbox delivery. No credentials
or OTPs are printed. All temporary users and the empty workspace are removed.
"""

import asyncio
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings, settings
from atlas import email_auth, main


async def run():
    config = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
    email_auth.settings = main.settings = lambda: config
    import atlas.db

    atlas.db.settings = lambda: config
    # Only delivery is replaced, retaining native code generation/verification,
    # durable rate limits, API identity checks, and all membership rules.
    codes, invitations = {}, []

    async def capture_code(email, code, purpose):
        codes[(email, purpose)] = code

    async def capture_invitation(email, workspace, url):
        invitations.append(url)

    email_auth.require_email_delivery = main.require_email_delivery = lambda: None
    email_auth.send_code = capture_code
    main.send_invitation = capture_invitation
    admin = {"apikey": config.supabase_service_role_key}
    public = {"apikey": config.supabase_publishable_key}
    base = config.supabase_url
    users, org = [], None
    async with (
        httpx.AsyncClient(timeout=30) as native,
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://test"
        ) as app,
    ):
        try:

            async def signup(label):
                email = (
                    "atlas-qa-email-"
                    + label
                    + "-"
                    + secrets.token_hex(4)
                    + "@example.com"
                )
                password = secrets.token_urlsafe(24)
                response = await app.post(
                    "/auth/email-code",
                    json={
                        "email": email,
                        "purpose": "signup",
                        "password": password,
                        "full_name": "Atlas QA Email " + label,
                    },
                )
                response.raise_for_status()
                assert "token" not in response.text and "password" not in response.text
                repeat = await app.post(
                    "/auth/email-code",
                    json={"email": email, "purpose": "signup", "password": password},
                )
                assert repeat.status_code == 429
                pending = await native.post(
                    base + "/auth/v1/token?grant_type=password",
                    headers=public,
                    json={"email": email, "password": password},
                )
                assert pending.is_error
                bad = await native.post(
                    base + "/auth/v1/verify",
                    headers=public,
                    json={"type": "email", "email": email, "token": "00000000"},
                )
                assert bad.is_error
                response = await native.post(
                    base + "/auth/v1/verify",
                    headers=public,
                    json={
                        "type": "email",
                        "email": email,
                        "token": codes[(email, "signup")],
                    },
                )
                response.raise_for_status()
                data = response.json()
                users.append(data["user"]["id"])
                assert data["user"]["email_confirmed_at"]
                reused = await native.post(
                    base + "/auth/v1/verify",
                    headers=public,
                    json={
                        "type": "email",
                        "email": email,
                        "token": codes[(email, "signup")],
                    },
                )
                assert reused.is_error
                return (
                    email,
                    password,
                    {"Authorization": "Bearer " + data["access_token"]},
                )

            owner = await signup("owner")
            teammate = await signup("teammate")
            stranger = await signup("stranger")
            response = await app.post(
                "/workspaces",
                headers=owner[2],
                json={
                    "name": "Atlas QA Company Email flows",
                    "full_name": "Atlas QA Email owner",
                },
            )
            response.raise_for_status()
            org = response.json()["id"]
            response = await app.post(
                f"/workspaces/{org}/invitations",
                headers=owner[2],
                json={"email": teammate[0]},
            )
            response.raise_for_status()
            assert response.json()["delivery"] == "sent"
            token = parse_qs(urlparse(invitations[0]).query)["invite"][0]
            wrong = await app.post(
                "/invitations/accept", headers=stranger[2], json={"token": token}
            )
            assert wrong.is_error
            response = await app.post(
                "/invitations/accept", headers=teammate[2], json={"token": token}
            )
            response.raise_for_status()
            assert response.json()["organization_id"] == org
            reused = await app.post(
                "/invitations/accept", headers=teammate[2], json={"token": token}
            )
            assert reused.is_error
            response = await app.get("/workspaces", headers=teammate[2])
            response.raise_for_status()
            assert any(
                row["id"] == org and row["role"] == "employee"
                for row in response.json()
            )
            # Advance only the synthetic recipient's cooldown to test recovery
            # immediately, without waiting or changing production settings.
            import hashlib, hmac

            key = hmac.new(
                config.supabase_service_role_key.encode(),
                ("auth:email:" + teammate[0]).encode(),
                hashlib.sha256,
            ).hexdigest()
            response = await native.patch(
                base + "/rest/v1/auth_email_limits",
                headers=admin,
                params={"key": "eq." + key},
                json={"last_sent": "2026-01-01T00:00:00Z"},
            )
            response.raise_for_status()
            response = await app.post(
                "/auth/email-code", json={"email": teammate[0], "purpose": "recovery"}
            )
            response.raise_for_status()
            response = await native.post(
                base + "/auth/v1/verify",
                headers=public,
                json={
                    "type": "recovery",
                    "email": teammate[0],
                    "token": codes[(teammate[0], "recovery")],
                },
            )
            response.raise_for_status()
            new_password = secrets.token_urlsafe(24)
            response = await native.put(
                base + "/auth/v1/user",
                headers={
                    **public,
                    "Authorization": "Bearer " + response.json()["access_token"],
                },
                json={"password": new_password},
            )
            response.raise_for_status()
            old = await native.post(
                base + "/auth/v1/token?grant_type=password",
                headers=public,
                json={"email": teammate[0], "password": teammate[1]},
            )
            assert old.is_error
            response = await native.post(
                base + "/auth/v1/token?grant_type=password",
                headers=public,
                json={"email": teammate[0], "password": new_password},
            )
            response.raise_for_status()
            print(
                {
                    "signup_pending_until_code": True,
                    "wrong_and_used_codes_rejected": True,
                    "resend_limit": True,
                    "invitation_verified_email_binding_and_replay_protection": True,
                    "employee_workspace_access": True,
                    "recovery_code_and_password_change": True,
                    "delivery": "captured locally; not an inbox delivery test",
                }
            )
        finally:
            if org:
                response = await native.delete(
                    base + "/rest/v1/organizations",
                    headers=admin,
                    params={"id": "eq." + org},
                )
                response.raise_for_status()
            for uid in users:
                response = await native.delete(
                    base + "/auth/v1/admin/users/" + uid, headers=admin
                )
                response.raise_for_status()
            print({"temporary_workspace_and_users_removed": True})


if __name__ == "__main__":
    asyncio.run(run())
