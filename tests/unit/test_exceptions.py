"""Application failures use a stable, safe response shape."""

from fastapi import Query
from fastapi.testclient import TestClient

from backend.app.core.exceptions import ApplicationError


def test_application_error_uses_public_code_and_message(client: TestClient) -> None:
    @client.app.get("/_test/application-error", include_in_schema=False)
    def raise_application_error() -> None:
        raise ApplicationError(
            status_code=409,
            code="phase_conflict",
            message="The requested phase cannot start yet.",
        )

    response = client.get("/_test/application-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "phase_conflict",
            "message": "The requested phase cannot start yet.",
        }
    }


def test_validation_error_uses_the_common_error_envelope(client: TestClient) -> None:
    @client.app.get("/_test/validation-error", include_in_schema=False)
    def require_positive(value: int = Query(gt=0)) -> dict[str, int]:
        return {"value": value}

    response = client.get("/_test/validation-error", params={"value": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "The request could not be validated."
    assert body["error"]["details"][0]["location"] == ["query", "value"]


def test_unexpected_error_does_not_leak_internal_details(client: TestClient) -> None:
    @client.app.get("/_test/unexpected-error", include_in_schema=False)
    def raise_unexpected_error() -> None:
        raise RuntimeError("database-password-should-never-leak")

    response = client.get("/_test/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred.",
        }
    }
    assert "database-password" not in response.text
