# app/tests/test_data_extraction.py
import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock
from app.main import app
from fastapi.testclient import TestClient
import tempfile
from app.routers.data_extraction import (
    normalize_user_id_column,
    create_random_password,
    encrypt_and_compress_files,
    upload_file_to_jira,
    def_jira_ticket_list,
)

# create TestClient
client = TestClient(app)


# create Mock object for Redis, Jira API, login_decorator
@pytest.fixture
def mock_redis_get():
    with patch("app.core.decorators.redis_client.get") as mock_get:
        # return json string
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


# test /data_extraction
# enhanced_search_issues 반환값
class MockEnhancedSearchResult:
    def __init__(self, issues, next_token=None):
        self._issues = issues
        self.nextPageToken = next_token

    def __iter__(self):
        return iter(self._issues)

    def __len__(self):
        return len(self._issues)


# Dummy Request
class DummyRequest:
    def __init__(self):
        self.cookies = {"session_id": "fake_session"}
        self.query_params = {}


@patch("app.routers.data_extraction.JIRA")
@patch("app.routers.auth.get_email_jira_token_value")
def test_def_jira_ticket_list(mock_get_jira_obj, mock_get_email_token):
    # session -> email, jira_api_token
    mock_get_email_token.return_value = ("fake_email@example.com", "fake_token")

    # Jira object Mock
    mock_jira = MagicMock()
    mock_get_jira_obj.return_value = mock_jira

    # search_issues.total mock
    mock_search_result = MagicMock()
    mock_search_result.total = 1
    mock_jira.search_issues.return_value = mock_search_result

    # Issue Mock
    mock_status = MagicMock()
    mock_status.name = "To Do"
    mock_fields = MagicMock()
    mock_fields.summary = "Test issue 1"
    mock_fields.status = mock_status

    mock_issue = MagicMock()
    mock_issue.key = "TEST-1"
    mock_issue.fields = mock_fields

    # enhanced_search_issues return value
    mock_jira.enhanced_search_issues.return_value = MockEnhancedSearchResult(
        [mock_issue]
    )

    # DummyRequest
    result = def_jira_ticket_list(DummyRequest)

    # assertion
    print(result)
    assert len(result["issues"]) == 1
    assert result["issues"][0]["key"] == "TEST-1"
    assert result["issues"][0]["summary"] == "Test issue 1"
    assert result["issues"][0]["status"] == "To Do"


# column normalize test
def test_normalize_user_id_column_basic():
    df = pd.DataFrame({"User ID": [1, 2], "Age": [20, 25]})
    normalized_df = normalize_user_id_column(df)
    assert isinstance(normalized_df, pd.DataFrame)
    # check if column name has changed into username
    assert any("username" in col for col in normalized_df.columns)


# random password creation test
def test_create_random_password_entropy():
    pw1 = create_random_password()
    pw2 = create_random_password()
    assert isinstance(pw1, bytes)
    assert pw1 != pw2
    assert len(pw1) > 16


# file encryption and compression test
def test_encrypt_and_compress_files_creates_zip(tmp_path):
    test_dir = tmp_path / "files"
    test_dir.mkdir()
    file_path = test_dir / "sample.txt"
    file_path.write_text("hello world")
    compressed_path, password = encrypt_and_compress_files(str(test_dir), "TEST-1")

    assert os.path.exists(compressed_path)
    assert compressed_path.endswith(".zip")
    assert isinstance(password, bytes)


# upload file to jira test
@patch("app.routers.data_extraction.send_slack_message")
def test_upload_file_to_jira_success(mock_slack):
    mock_jira = MagicMock()
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(b"data")
    tmp.close()

    result = upload_file_to_jira(mock_jira, tmp.name, "TICKET-123")

    assert result["status"] == "success"
    mock_jira.add_attachment.assert_called_once()
    mock_jira.add_comment.assert_called_once()
    mock_slack.assert_called_once()
    os.unlink(tmp.name)
