"""HTTP-level checks for the Phase 1 application shell."""

from fastapi.testclient import TestClient


def test_root_describes_the_service(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "NovaEnterprise",
        "status": "available",
        "version": "0.1.0",
    }


def test_liveness_route_is_small_and_deterministic(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"service": "NovaEnterprise", "status": "ok"}


def test_openapi_exposes_the_implemented_system_and_auth_routes(client: TestClient) -> None:
    document = client.get("/openapi.json").json()

    assert document["info"]["title"] == "NovaEnterprise"
    assert set(document["paths"]) == {
        "/",
        "/health/live",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
    }
