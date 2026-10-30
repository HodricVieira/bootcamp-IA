from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "DocuMind API"}


def test_public_config_does_not_expose_service_role_key() -> None:
    response = client.get("/config/public")
    assert response.status_code == 200
    assert response.json() == {
        "supabase_url": "",
        "supabase_publishable_key": "",
    }


def test_documents_require_authentication() -> None:
    from app.core.auth import get_current_user

    override = app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post("/documents/upload", files={"file": ("empty.pdf", b"", "application/pdf")})
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "UNAUTHORIZED"
    finally:
        if override is not None:
            app.dependency_overrides[get_current_user] = override
