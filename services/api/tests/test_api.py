from fastapi.testclient import TestClient
from atlas.main import app

client = TestClient(app)


def test_private_endpoints_require_authentication():
    assert client.get("/workspaces").status_code == 401
    assert client.post("/workspaces", json={"name": "Acme"}).status_code == 401
    assert client.get("/documents/00000000-0000-0000-0000-000000000001/source").status_code == 401


def test_safe_health_and_file_capabilities():
    assert client.get("/health/live").json()["status"] == "ok"
    capabilities = client.get("/capabilities").json()
    assert ".docx" in capabilities["extensions"]
    assert ".exe" not in capabilities["extensions"]
    assert capabilities["auth_required"] is True
    assert client.get("/health/live").headers["x-content-type-options"] == "nosniff"
