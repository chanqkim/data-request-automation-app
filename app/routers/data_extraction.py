from fastapi import APIRouter, Request
from app.core.templates import templates
from app.core.decorators import is_logged_in
from app.routers.auth import get_email_jira_token_value
from app.config import JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_MAX_RESULTS
import requests

router = APIRouter()


# get Jira data request ticket list
def def_jira_ticket_list(request):
    # Jira authenthication
    url = f"{JIRA_BASE_URL}/rest/api/3/search"
    query = {
        "jql": f"project={JIRA_PROJECT_KEY} ORDER BY created DESC",
        "maxResults": JIRA_MAX_RESULTS,
    }
    session_id = request.cookies.get("session_id")
    email, jira_api_token = get_email_jira_token_value(session_id)
    auth = (email, jira_api_token)
    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers, params=query, auth=auth)

    if response.status_code != 200:
        print(f"❌ Jira API Error: {response.status_code}, {response.text}")
        return []

    # get jira ticket lists
    raw_issues = response.json().get("issues", [])

    # parse ticket lists and return list to data_extraction.html
    issue_lists = []
    for issue in raw_issues:
        try:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "")
            status = fields.get("status", {}).get("name", "")

            issue_lists.append({"key": key, "summary": summary, "status": status})
        except Exception as e:
            print(f"Failed to parse issue {issue.get('key')}: {e}")

    return issue_lists


@router.get("/data_extraction")
@is_logged_in
def data_extraction_page(request: Request):
    # check cookies
    tickets = def_jira_ticket_list(request)

    # render data-extract template
    return templates.TemplateResponse(
        "data_extraction.html", {"request": request, "tickets": tickets}
    )
