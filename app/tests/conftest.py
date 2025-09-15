import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers import data_extraction


@pytest.fixture
def client():
    app.include_router(data_extraction.router)
    return TestClient(app)
