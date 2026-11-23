"""Phase 3 authentication and request guards work fully offline."""

from fastapi import Depends
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.security import AuthenticatedUser, require_role
from backend.app.main import create_app
from backend.app.schemas.common import UserRole


def test_demo_login_issues_role_scoped_token_and_me_response(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": "demo-analyst"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["role"] == "analyst"
    assert "password" not in payload

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json() == payload["user"]


def test_authentication_and_central_rbac_reject_missing_or_insufficient_role() -> None:
    app = create_app(Settings(app_env="test"))

    @app.post("/analyst-only")
    def analyst_only(
        user: AuthenticatedUser = Depends(require_role(UserRole.ANALYST)),
    ) -> dict[str, str]:
        return {"user_id": user.id}

    with TestClient(app) as test_client:
        missing = test_client.post("/analyst-only")
        viewer_token = test_client.post(
            "/api/v1/auth/login",
            json={"username": "viewer", "password": "demo-viewer"},
        ).json()["access_token"]
        denied = test_client.post(
            "/analyst-only", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        admin_token = test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "demo-admin"},
        ).json()["access_token"]
        allowed = test_client.post(
            "/analyst-only", headers={"Authorization": f"Bearer {admin_token}"}
        )

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_role"
    assert allowed.status_code == 200


def test_invalid_login_and_tampered_token_are_rejected(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "analyst", "password": "wrong"},
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "invalid_credentials"

    tampered = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer x.y.z"})
    assert tampered.status_code == 401
    assert tampered.json()["error"]["code"] == "invalid_token"


def test_request_id_rate_limit_and_audit_middleware_order() -> None:
    app = create_app(Settings(app_env="test", rate_limit_per_minute=2))
    with TestClient(app) as test_client:
        first = test_client.get("/", headers={"X-Request-ID": "interview-request-1"})
        second = test_client.get("/")
        limited = test_client.get("/")

    assert first.headers["X-Request-ID"] == "interview-request-1"
    assert second.headers["X-Request-ID"]
    assert limited.status_code == 429
    assert limited.headers["X-Request-ID"]
    assert limited.json()["error"]["code"] == "rate_limit_exceeded"
    records = app.state.audit_trail.records()
    assert [record.status_code for record in records] == [200, 200, 429]
    assert records[-1].request_id == limited.headers["X-Request-ID"]


def test_untrusted_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/", headers={"X-Request-ID": "bad id with spaces"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad id with spaces"


def test_request_id_is_present_on_unexpected_errors() -> None:
    app = create_app(Settings(app_env="test"))

    @app.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("private detail")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/unexpected")

    assert response.status_code == 500
    assert response.headers["X-Request-ID"]
    assert response.json()["error"]["code"] == "internal_error"


def test_auth_routes_honor_configured_prefix_and_tenant() -> None:
    app = create_app(
        Settings(app_env="test", api_prefix="/internal/v1", default_tenant_id="tenant-custom")
    )
    with TestClient(app) as test_client:
        login = test_client.post(
            "/internal/v1/auth/login",
            json={"username": "viewer", "password": "demo-viewer"},
        )

    assert login.status_code == 200
    assert login.json()["user"]["tenant_id"] == "tenant-custom"


def test_demo_login_is_disabled_outside_local_and_test() -> None:
    app = create_app(Settings(app_env="staging"))
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "viewer", "password": "demo-viewer"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "demo_auth_disabled"
