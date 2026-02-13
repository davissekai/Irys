from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ocr_provider"] == "glm"


def test_root_ready():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "ocr_provider" in data
