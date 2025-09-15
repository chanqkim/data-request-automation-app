# app/tests/test_data_extraction.py
import pytest
from unittest.mock import patch, MagicMock


# create Mock object for Redis, Jira API, login_decorator
@pytest.fixture
def mock_redis_get():
    with patch("app.core.decorators.redis_client.get") as mock_get:
        # JSON 문자열 형태로 반환
        mock_get.return_value = '{"user_email": "fake_email@example.com"}'
        yield mock_get


@pytest.fixture
def mock_get_email_jira_token_value():
    with patch("app.routers.auth.get_email_jira_token_value") as mock_func:
        mock_func.return_value = ("fake_email@example.com", "fake_jira_token")
        yield mock_func


@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock_req:
        # Jira API Mock Response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "issues": [
                {
                    "key": "TEST-1",
                    "fields": {"summary": "Test issue 1", "status": {"name": "To Do"}},
                },
                {
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Test issue 2",
                        "status": {"name": "In Progress"},
                    },
                },
            ]
        }
        mock_req.return_value = mock_resp
        yield mock_req


# 실제 테스트 함수
def test_data_extraction_page_route(
    client, mock_redis_get, mock_get_email_jira_token_value, mock_requests_get
):
    response = client.get("/data_extraction", cookies={"session_id": "fake_session_id"})
    assert response.status_code == 200
    data = response.text
    assert "TEST-1" in data
    assert "TEST-2" in data
    assert "Test issue 1" in data
    assert "Test issue 2" in data
