# import pytest
from fastapi.testclient import TestClient
from app.main import app  # main.py에 있는 FastAPI 앱 import

client = TestClient(app)


# test if first page lands to /login
def test_root_redirect():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/login"


# test if health endpoint works
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "data-request-automation-app is active"}
