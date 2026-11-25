from fastapi.testclient import TestClient

from app.main import app


def test_cors_allowed_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_disallowed_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://malicious-origin.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORSMiddleware returns 200 for OPTIONS even on disallowed origins,
    # but does NOT include the Access-Control-Allow-Origin header.
    assert response.headers.get("access-control-allow-origin") is None
