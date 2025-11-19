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

from app.config import (
    CHUNK_SIZE,
    FILE_PATH,
    JIRA_ADMIN_GROUP,
    JIRA_BASE_URL,
    JIRA_PROJECT_KEY,
    JIRA_TICKETS_PER_PAGE,
    SLACK_WEBHOOK_URL,
)
from app.core.db_connection import get_db_connection, save_log_to_mysql
from app.core.decorators import is_logged_in
from app.core.logger import logger
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
        logger.error(f"❌ Jira API Error: {e}")
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


# fix column names to normalize user_id column
def normalize_user_id_column(df: pd.DataFrame) -> pd.DataFrame:
    # normalize column names in original df
    normalized_cols = {col: col.strip().lower() for col in df.columns}
    df = df.rename(columns=normalized_cols)

    # column name candidates that needs to be fixed to user_id
    candidates = [
        "User ID",
        "user id",
        "id",
        "USER_ID",
        "UserId",
        "userid",
        "User Name",
        "user name",
        "user_name",
    ]

    # check existing columns and rename if matches
    for col in df.columns:
        if col in candidates:
            df = df.rename(columns={col: "username"})

    # return original df
    return df


# get pii data from users table by username list
def fetch_users_by_user_ids(username_list: list, conn) -> pd.DataFrame:
    """
    Get PII-related user data efficiently from MySQL Users table
    """
    query = """
        SELECT username, email, gender
        FROM users
        WHERE username IN %(username_list)s
    """

    return pd.read_sql(query, conn, params={"username_list": tuple(username_list)})


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
        logger.info("✅ Slack message sent successfully!")
    else:
        logger.error(
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
@router.post("/extract/{ticket_key}", response_model=None)
async def get_data_from_query(request: Request, ticket_key: str):
    """
    add PII_data that matches DataFrame
    """
    jira = get_jira_object(request)
    # get file_lists that was attached in jira ticket
    attached_files_list = await get_jira_ticket_attached_data(jira, ticket_key)

    # extract data if files exist
    if len(attached_files_list) > 0:
        conn = get_db_connection()

        # use loop to open file
        for file in attached_files_list:
            file_lower = str(file).lower()
            file_name = file.split("/")[-1].split(".")[0]
            logger.info(f"Processing file: {file_name}")
            # check file extension and read file accordingly
            try:
                # CSV
                if file_lower.endswith(".csv"):
                    file_df = pd.read_csv(file)

                # Excel (xlsx, xls)
                elif file_lower.endswith(".xlsx") or file_lower.endswith(".xls"):
                    file_df = pd.read_excel(file)

                # fix column names
                file_df = normalize_user_id_column(file_df).dropna(subset=["username"])
                logger.info(
                    f"normalized {file_name} columns, columns: {file_df.columns}"
                )

                # create final file path
                final_file_path = f"/file_path/{ticket_key}"
                if not os.path.isdir(final_file_path):
                    os.makedirs(final_file_path, exist_ok=True)
                logger.info(f"created extraction file dir: {final_file_path}")

                first_write = True  # check first write for append mode
                # divide dataframe into chunks to avoid memory issues
                logger.info(f"dividing {file_name} into chunks of size {CHUNK_SIZE}")
                for i in range(0, len(file_df), CHUNK_SIZE):
                    chunk_file_df = file_df.iloc[i : i + CHUNK_SIZE]

                    # get unique usernames in chunk
                    chunk_usernames = chunk_file_df["username"].unique().tolist()

                    # fetch pii data from db
                    db_data_chunk = fetch_users_by_user_ids(chunk_usernames, conn)

                    # merge chunk file df with db data
                    merged_df = chunk_file_df.merge(
                        db_data_chunk, on="username", how="left"
                    )

                    save_file_name = f"{final_file_path}/{file_name}.csv"
                    merged_df.to_csv(
                        save_file_name,
                        index=False,
                        append=not first_write,
                    )
                    first_write = False  # after first loop append data
                logger.info(f"saved extracted data to {save_file_name}")

            except Exception as e:
                logger.error(
                    f"Error reading file {file}: {e}, expected format CSV or Excel."
                )

        # compress and encrypt file
        logger.info(f"compressing and encrypting extracted files in {final_file_path}")

        compressed_file_path, password = encrypt_and_compress_files(
            final_file_path, ticket_key
        )
        logger.info(f"data compressed to {compressed_file_path}")

        upload_file_to_jira(jira, compressed_file_path, ticket_key)
        logger.info(f"attached compress data to jira ticket {ticket_key}")

        # send slack message
        comment_text = (
            f"✅ Jira ticket **{ticket_key}** has been successfully delivered.\n\n"
            f"The extracted data is encrypted for security. "
            f"Please use the following password to access the data: `{password}`\n\n"
            f"If you encounter any issues or discrepancies in the extracted data, "
            f"please contact **Data Team**."
        )
        send_slack_message(SLACK_WEBHOOK_URL, comment_text)
        logger.info(f"sent slack message for ticket {ticket_key}")

        # saving log to MySQL
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise ValueError("No session_id found in request cookies.")
        jira_email, _ = get_email_jira_token_value(session_id)

        save_log_to_mysql(
            extractor_id=jira_email,
            ticket_key=ticket_key,
            file_path=compressed_file_path,
        )


# create random password
def create_random_password():
    # Generate random 32-byte key material and encode as Base64 string
    random_bytes = secrets.token_bytes(32)
    random_password = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
    password_bytes = random_password.encode("utf-8")
    return password_bytes


# encrypt query data and compress zip file
def encrypt_and_compress_files(final_file_path: str, ticket_no: str) -> list[str, str]:
    """
    Encrypt and compress all files inside a directory (no subfolder recursion).
    Files are added flat into a single AES-encrypted zip.

    Args:
        directory_path (str): Directory containing the files.
        zip_name (str): Output zip filename. Default: "files.zip"

    Returns:
       [output_zip_path, password]: path to created zip + generated password.
    """

    # set Password
    password = create_random_password()

    # zip output path
    compressed_file_path = os.path.join(final_file_path, f"{ticket_no}.zip")

    with pyzipper.AESZipFile(
        compressed_file_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password)

        # iterate through only files in final_file_path
        for file in os.listdir(final_file_path):
            full_path = os.path.join(final_file_path, file)

            # skip the zip file itself (re-run safety)
            if full_path == compressed_file_path:
                continue

            # include only files, no directories
            if os.path.isfile(full_path):
                with open(full_path, "rb") as f:
                    zf.writestr(file, f.read())  # Store plain filename

    return compressed_file_path, password


# attach zip file to jira ticket
def upload_file_to_jira(
    jira: JIRA,
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

    try:
        with open(file_path, "rb") as f:
            jira.add_attachment(
                issue=ticket_no, attachment=f, filename=os.path.basename(file_path)
            )

        # adding additional comments in the ticket
        comment_text = (
            f"✅ Jira ticket **{ticket_no}** has been successfully delivered.\n\n"
            f"If you encounter any issues or discrepancies in the extracted data, "
            f"please contact **Data team**."
        )

        jira.add_comment(ticket_no, comment_text)
        logger.info(f"📎 File '{file_path}' attached successfully to {ticket_no}")

        # sending message bia slack
        send_slack_message(SLACK_WEBHOOK_URL, comment_text)

        return {"status": "success", "file": os.path.basename(file_path)}

    except JIRAError as e:
        logger.error(
            f"❌ Jira API error while attaching file: {e.status_code} - {e.text}"
        )
        return {"status": "error", "code": e.status_code, "details": e.text}

    except Exception as e:
        logger.error(f"⚠️ Unexpected error: {e}")
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
