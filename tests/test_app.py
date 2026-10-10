"""Foundation HTTP smoke tests; no database connection is needed."""
from fastapi.testclient import TestClient


def test_root_renders_starter_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "ContentPilot Test" in response.text
    assert "Status: running" in response.text


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_api_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"service": "content-pilot", "status": "ok"}
