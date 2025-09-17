from fastapi import APIRouter, Request, HTTPException
from app.core.templates import templates
from app.core.decorators import is_logged_in
from app.routers.auth import get_email_jira_token_value
from app.config import (
    JIRA_BASE_URL,
    JIRA_ADMIN_GROUP,
    JIRA_PROJECT_KEY,
    JIRA_MAX_RESULTS,
)
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
        raise HTTPException(
            status_code=response.status_code,
            detail=f"❌ Jira API Error: {response.status_code}, {response.text}",
        )

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


# check whether ticket has pii info
def is_pii_ticket(email, jira_api_token, ticket_id):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_id}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, auth=(email, jira_api_token), headers=headers)

    # raise error if failed to receive response
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    issue_data = response.json()
    pii_field = issue_data["fields"].get("customfield_10071")

    # raise error if custom field is None
    if not pii_field:
        return False

    # 만약 필드가 객체형이면 'value' 사용, 문자열이면 그대로 비교
    pii_value = pii_field["value"]

    if pii_value == "Y":
        return True


# check whether current user has admin status
def is_jira_admin(email, jira_api_token) -> bool:
    url = f"{JIRA_BASE_URL}/rest/api/3/group/member?groupname={JIRA_ADMIN_GROUP}"
    response = requests.get(url, auth=(email, jira_api_token))

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch jira_admin group members: {response.text}",
        )

    admin_email_list = [
        i["emailAddress"] for i in response.json()["values"] if i.get("emailAddress")
    ]

    return email in admin_email_list


# approve PII data extraction jira ticket
def approve_pii_jira_ticket(request, ticket_id):
    session_id = request.cookies.get("session_id")
    email, jira_api_token = get_email_jira_token_value(session_id)

    # check if ticket is requesting PII data, thus needs approval
    pii_ticket = is_pii_ticket(email, jira_api_token, ticket_id)

    # alert user that this ticket does not have PII, thus does not require admin's approval
    if not pii_ticket:
        pass

    # check if user has jira-admin status
    jira_admin_status = is_jira_admin(email, jira_api_token)

    if not jira_admin_status:
        raise HTTPException(
            status_code=403,
            detail="User does not have Jira Admin privileges",
        )

    # if login user is in the admin_email_list, approve the jira ticket


# get data from query
def get_data_from_query():
    pass


# encrypt query data and compress zip file
def encrypt_and_compress_data():
    pass


# attach zip file to jira ticket
def upload_file_to_jira():
    pass


@router.get("/data_extraction")
@is_logged_in
def data_extraction_page(request: Request):
    # check cookies
    tickets = def_jira_ticket_list(request)

    # render data-extract template
    return templates.TemplateResponse(
        "data_extraction.html", {"request": request, "tickets": tickets}
    )
