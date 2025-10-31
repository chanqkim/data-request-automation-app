import base64
import json
import os
import secrets
import zipfile
from math import ceil

import pandas as pd
import pyzipper
import requests
from fastapi import APIRouter, HTTPException, Request
from jira import JIRA, JIRAError
from pandas import DataFrame

from app.config import (
    FILE_PATH,
    JIRA_ADMIN_GROUP,
    JIRA_BASE_URL,
    JIRA_MAX_RESULTS,
    JIRA_PROJECT_KEY,
    JIRA_TICKETS_PER_PAGE,
    SLACK_WEBHOOK_URL,
)
from app.core.decorators import is_logged_in
from app.core.templates import templates
from app.routers.auth import get_email_jira_token_value

router = APIRouter()


def get_jira_object(request: str) -> JIRA:
    """
    return Jira object that is used to approve data extraction, download file, attach file

    Args:
        request (str): web request
    Returns:
        jira object
    Raises:
        ValueError: if session_id is missing or Jira authentication fails
    """

    try:
        # get jira authetntication info from session
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise ValueError("No session_id found in request cookies.")

        jira_email, jira_api_token = get_email_jira_token_value(session_id)
        if not jira_email or not jira_api_token:
            raise ValueError("Could not retrieve Jira email or API token from session.")

        # Connect to Jira
        jira = JIRA(server=JIRA_BASE_URL, basic_auth=(jira_email, jira_api_token))
        return jira

    except JIRAError as e:
        # Jira server connection fail / authentication fail
        raise ConnectionError(f"Failed to connect to Jira: {e.text}") from e
    except HTTPException as e:
        # Network error
        raise ConnectionError(
            f"Network error while connecting to Jira: {str(e)}"
        ) from e
    except Exception as e:
        # other exceptions
        raise RuntimeError(
            f"Unexpected error while initializing Jira client: {str(e)}"
        ) from e


# get Jira data request ticket list
def def_jira_ticket_list(request: Request, next_page_token: str | None = None):
    try:
        session_id = request.cookies.get("session_id")
        email, jira_api_token = get_email_jira_token_value(session_id)
        jira = JIRA(server=JIRA_BASE_URL, basic_auth=(email, jira_api_token))

        jql_query = f"project={JIRA_PROJECT_KEY} and 'PII_YN'='Y' ORDER BY created DESC"

        # get total ticket counts
        total_issues = jira.search_issues(jql_str=jql_query, maxResults=0).total
        total_pages = ceil(total_issues / JIRA_TICKETS_PER_PAGE)

        # use enhanced_search_issues to get nextPageToken
        kwargs = {"jql_str": jql_query, "maxResults": JIRA_TICKETS_PER_PAGE}
        if next_page_token:
            kwargs["nextPageToken"] = next_page_token

        result = jira.enhanced_search_issues(**kwargs)
        issues = list(result)
        next_token = getattr(result, "nextPageToken", None)

        # prepare issue list object for response
        issue_lists = [
            {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
            }
            for issue in issues
        ]

        # calculate current page
        if next_page_token:
            current_page = int(request.query_params.get("page", 1))
        else:
            current_page = 1

        return {
            "issues": issue_lists,
            "next_page_token": next_token or "",
            "current_page": current_page,
            "total_issues": total_issues,
            "total_pages": total_pages,
        }

    except Exception as e:
        print(f"❌ Jira API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Jira issues: {e}")


# render data extraction page using pagination
@router.get("/data_extraction")
def data_extraction_page(
    request: Request, next_page_token: str | None = None, page: int = 1
):
    # get paginated jira ticket list
    jira_data = def_jira_ticket_list(request, next_page_token)

    return templates.TemplateResponse(
        "data_extraction.html",
        {
            "request": request,
            "tickets": jira_data["issues"],
            "current_page": page,
            "total_pages": jira_data["total_pages"],
            "total_issues": jira_data["total_issues"],
            "next_page_token": jira_data["next_page_token"],
        },
    )


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
@router.post("/approve/{ticket_id}")
async def approve_pii_jira_ticket(request, ticket_id):
    """
    Approve ticket by changing ticket status from Request Submission -> Request Approval

    Args:
        request (str): web request
        ticket_id (str): jira issue key
    Returns:
        dict: API response JSON or error message
    """

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

    # create jira instance
    # jira = JIRA(server=JIRA_BASE_URL, basic_auth=(email, jira_api_token))
    jira = get_jira_object(request)
    # if login user is in the admin_email_list, approve the jira ticket
    # get ticket object
    issue = jira.issue(ticket_id)

    # check transition
    transitions = jira.transitions(issue)
    transition_name = "Approve Data Extraction Request"  # Jira status name for tickets that has been approved for data extraction

    transition_id = None
    for t in transitions:
        if t["name"].lower() == transition_name.lower():
            transition_id = t["id"]
            break

    # raise error if transition_id for transation_name does not exist
    if not transition_id:
        raise HTTPException(
            status_code=400,
            detail=f"Transition '{transition_name}' not available for ticket {ticket_id}.",
        )

    # change ticket status for To-Do -> Request Approved
    jira.transition_issue(issue, transition_id)
    print(f"✅ Ticket {ticket_id} successfully transitioned via '{transition_name}'.")

    # Add request approval comment
    comment_text = (
        f"✅ Ticket {ticket_id} has been approved for PII extraction by {email}."
    )
    jira.add_comment(issue, comment_text)

    # Add request approval comment via slack
    send_slack_message(SLACK_WEBHOOK_URL, comment_text)

    return {
        "message": f"Ticket {ticket_id} transitioned to 'Approved' and comment added."
    }


# send slack message
def send_slack_message(
    webhook_url, message, username="Data Bot", icon_emoji=":robot_face:"
):
    payload = {
        "username": username,
        "icon_emoji": icon_emoji,
        "text": message,
    }

    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        print("✅ Slack message sent successfully!")
    else:
        print(
            f"❌ Failed to send message. Status: {response.status_code}, Response: {response.text}"
        )


# get data attached in Jira ticket
async def get_jira_ticket_attached_data(jira: JIRA, ticket_no: str):
    """
    add save file attached to the Jira ticket
    """

    # create dir to download files attached in jira
    os.makedirs(FILE_PATH, exist_ok=True)
    issue = jira.issue(ticket_no)
    attachment_paths = []

    for attachment in issue.fields.attachment:
        local_path = os.path.join(FILE_PATH, attachment.filename)

        # us Jira library to get files in binary
        file_content = attachment.get()  # bytes

        with open(local_path, "wb") as f:
            f.write(file_content)

        attachment_paths.append(local_path)

    return attachment_paths


# get data from query
def get_data_from_query(jira: JIRA, ticket_no: str, df: DataFrame) -> DataFrame:
    """
    add PII_data that matches DataFrame
    """

    # get file_lists that was attached in jira ticket
    attached_files_list = get_jira_ticket_attached_data(jira, ticket_no)

    # extract data if files exist
    if len(attached_files_list) > 0:
        # use loop to open file
        for file in attached_files_list:
            file_df = pd.read_csv(DataFrame)
    return file_df


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

        # sending message bia slack
        send_slack_message(SLACK_WEBHOOK_URL, comment_text)

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
