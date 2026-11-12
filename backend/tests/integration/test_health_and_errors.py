"""Integration tests for health endpoint, middleware, and error handlers."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.main import create_app


def test_health_endpoint_returns_expected_contract(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Site Shield AI"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
    assert "timestamp" in body
    assert body["dependencies"]["vector_db"]["status"] == "not_configured"
    assert body["dependencies"]["embedding"]["status"] == "not_configured"
    assert body["dependencies"]["llm"]["status"] == "not_configured"


def test_health_echoes_valid_request_id_and_replaces_invalid(client: TestClient) -> None:
    valid_res = client.get("/health", headers={"X-Request-ID": "trace-42_ok"})
    assert valid_res.status_code == 200
    assert valid_res.headers["X-Request-ID"] == "trace-42_ok"

    invalid_res = client.get("/health", headers={"X-Request-ID": "bad header with spaces!"})
    assert invalid_res.status_code == 200
    assert invalid_res.headers["X-Request-ID"] != "bad header with spaces!"


def test_404_uses_standard_error_envelope(client: TestClient) -> None:
    res = client.get("/nonexistent-route", headers={"X-Request-ID": "req-404-test"})
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "HTTP_404"
    assert body["error"]["request_id"] == "req-404-test"


def test_app_error_and_unexpected_exception_handlers(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    test_router = APIRouter()

    @test_router.get("/_test/not-found")
    async def raise_not_found() -> None:
        raise ResourceNotFoundError("Document doc_999 was not found.")

    @test_router.get("/_test/crash")
    async def raise_crash() -> None:
        raise RuntimeError("sensitive internal detail should not leak")

    @test_router.get("/_test/items/{item_id}")
    async def typed_param(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    app.include_router(test_router)

    with TestClient(app, raise_server_exceptions=False) as local_client:
        r_not_found = local_client.get("/_test/not-found", headers={"X-Request-ID": "req-app-err"})
        assert r_not_found.status_code == 404
        assert r_not_found.json()["error"] == {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Document doc_999 was not found.",
            "request_id": "req-app-err",
        }

        r_validation = local_client.get("/_test/items/not-an-int")
        assert r_validation.status_code == 422
        assert r_validation.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"
        assert isinstance(r_validation.json()["error"]["details"], list)

        r_crash = local_client.get("/_test/crash", headers={"X-Request-ID": "req-500"})
        assert r_crash.status_code == 500
        assert r_crash.headers["X-Request-ID"] == "req-500"
        crash_body = r_crash.json()
        assert crash_body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert crash_body["error"]["message"] == "An internal server error occurred."
        assert crash_body["error"]["request_id"] == "req-500"
        assert "sensitive internal detail" not in r_crash.text


def test_cors_headers_on_preflight(client: TestClient) -> None:
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

