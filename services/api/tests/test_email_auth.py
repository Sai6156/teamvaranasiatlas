import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from atlas.main import app
from atlas import email_auth


def configure(monkeypatch, response):
    delivered = []
    monkeypatch.setattr(email_auth, "require_email_delivery", lambda: None)

    async def reserve(*args):
        return None

    async def send(email, code, purpose):
        delivered.append((email, code, purpose))

    class DB:
        base = "https://auth.example.test"
        headers = {"apikey": "server-only"}

        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(email_auth, "Database", DB)
    monkeypatch.setattr(email_auth, "reserve_email", reserve)
    monkeypatch.setattr(email_auth, "send_code", send)
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: response)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=transport)
    )
    return delivered


def test_signup_sends_native_code_without_exposing_any_credentials(monkeypatch):
    delivered = configure(
        monkeypatch,
        httpx.Response(
            200, json={"email_otp": "123456", "hashed_token": "private-hash"}
        ),
    )
    result = TestClient(app).post(
        "/auth/email-code",
        json={
            "email": "Person@example.com",
            "purpose": "signup",
            "password": "private-password-123",
        },
    )
    assert result.status_code == 202
    assert delivered == [("person@example.com", "123456", "signup")]
    assert not any(
        value in result.text
        for value in ("123456", "private-hash", "private-password-123", "server-only")
    )


def test_unknown_recovery_email_returns_generic_success_without_sending(monkeypatch):
    delivered = configure(
        monkeypatch, httpx.Response(404, json={"error_code": "user_not_found"})
    )
    result = TestClient(app).post(
        "/auth/email-code", json={"email": "unknown@example.com", "purpose": "recovery"}
    )
    assert result.status_code == 202
    assert delivered == []
    assert "eligible" in result.json()["message"]


def test_request_limit_prevents_code_generation_and_delivery(monkeypatch):
    delivered = configure(
        monkeypatch, httpx.Response(200, json={"email_otp": "123456"})
    )

    async def denied(*args):
        raise HTTPException(429, "Please wait.")

    monkeypatch.setattr(email_auth, "reserve_email", denied)
    result = TestClient(app).post(
        "/auth/email-code", json={"email": "person@example.com", "purpose": "recovery"}
    )
    assert result.status_code == 429
    assert delivered == []


def test_signup_requires_strong_password_before_creating_user(monkeypatch):
    delivered = configure(
        monkeypatch, httpx.Response(200, json={"email_otp": "123456"})
    )
    client = TestClient(app)
    for body in (
        {"email": "person@example.com", "purpose": "signup"},
        {"email": "person@example.com", "purpose": "signup", "password": "short"},
    ):
        assert client.post("/auth/email-code", json=body).status_code == 422
    assert delivered == []
