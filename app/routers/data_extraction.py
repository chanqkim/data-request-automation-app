from fastapi import APIRouter, Request, HTTPException
from app.core.templates import templates
from app.core.decorators import is_logged_in
from app.routers.auth import get_email_jira_token_value
from app.config import (
    JIRA_BASE_URL,
    JIRA_ADMIN_GROUP,
    JIRA_PROJECT_KEY,
    JIRA_MAX_RESULTS,
    FILE_PATH,
)
import requests
import os
import zipfile
import secrets
import base64
import pyzipper
from jira import JIRA, JIRAError

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


# create random password
def create_random_password():
    # Generate random 32-byte key material and encode as Base64 string
    random_bytes = secrets.token_bytes(32)
    random_password = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
    password_bytes = random_password.encode("utf-8")
    return password_bytes


# encrypt query data and compress zip file
def encrypt_and_compress_data(file_name):
    # decide output path
    output_zip_dir = os.path.join(FILE_PATH, os.path.splitext(file_name)[0] + ".zip")

    # create password
    password = create_random_password()

    # read the input file (for single-file use)
    with open(FILE_PATH + file_name, "rb") as f:
        file_data = f.read()

    # create AES-encrypted zip (WZ_AES -> AES encryption in ZIP)
    # compression uses DEFLATED; encryption uses AES (stronger than legacy ZipCrypto)
    with pyzipper.AESZipFile(
        output_zip_dir,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password)  # set password (bytes)
        # write the file into the archive; the archive entry will be encrypted
        zf.writestr(os.path.basename(file_name), file_data)

    # return the password string so the caller can save/transmit it securely
    return password


# attach zip file to jira ticket


def upload_file_to_jira(
    jira_email: str,
    jira_api_token: str,
    file_path: str,
    ticket_no: str,
):
    """
    adding extracted file to jira ticket

    Args:
        file_path (str): extracted file dir
        ticket_no (str): jira issue key
    Returns:
        dict: API response JSON or error message 또는 에러 메시지
    """

    jira = JIRA(server=JIRA_BASE_URL, basic_auth=(jira_email, jira_api_token))

    issue = jira.issue(ticket_no)

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        with open(file_path, "rb") as f:
            jira.add_attachment(
                issue=issue, attachment=f, filename=os.path.basename(file_path)
            )

        # adding additional comments in the ticket
        comment_text = (
            f"✅ Jira ticket **{ticket_no}** has been successfully delivered.\n\n"
            f"If you encounter any issues or discrepancies in the extracted data, "
            f"please contact **{jira_email}**."
        )

        jira.add_comment(issue, comment_text)
        print(f"📎 File '{file_path}' attached successfully to {ticket_no}")

        return {"status": "success", "file": os.path.basename(file_path)}

    except JIRAError as e:
        # JIRAError 는 HTTP 응답코드, 텍스트 등을 포함
        print(f"❌ Jira API error while attaching file: {e.status_code} - {e.text}")
        return {"status": "error", "code": e.status_code, "details": e.text}

    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return {"status": "error", "details": str(e)}


@router.get("/data_extraction")
@is_logged_in
def data_extraction_page(request: Request):
    # check cookies
    tickets = def_jira_ticket_list(request)

    # render data-extract template
    return templates.TemplateResponse(
        "data_extraction.html", {"request": request, "tickets": tickets}
    )
