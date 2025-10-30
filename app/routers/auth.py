import json
import uuid

import requests
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import JIRA_BASE_URL, SESSION_COOKIE_NAME, SESSION_EXPIRE_SECONDS
from app.core.logger import logger
from app.core.redis_client import redis_client
from app.core.templates import templates

router = APIRouter()


# create session
def create_session(user_email: str, jira_api_token: str) -> str:
    "add user_email to redis to create session"

    # create session
    session_id = str(uuid.uuid4())

    # create session data
    session_data = {"user_email": user_email, "jira_api_token": jira_api_token}
    logger.info(f"Creating session for user: {user_email}, session_id: {session_id}")
    redis_client.setex(session_id, SESSION_EXPIRE_SECONDS, json.dumps(session_data))

    return session_id


# get user_email, jira api token
def get_email_jira_token_value(session_id: str):
    """get email, jira api token value from Redis"""
    value = redis_client.get(session_id)

    # session expired or session does not exist
    if not value:
        logger.info(f"{session_id} not in redis")
        return None, None
    session_data = json.loads(value)

    email = session_data.get("user_email")
    jira_api_token = session_data.get("jira_api_token")

    return email, jira_api_token


# land to login page
@router.get("/login")
def login_page(request: Request, error: str = None):
    # if session exists, move to /menu page
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id and redis_client.get(session_id):
        return RedirectResponse(url="/menu", status_code=302)
    else:
        logger.info("session_id does not exist or session has expired")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": error}
        )


# login using redis as session
@router.post("/login")
def login(
    email: str = Form(...),
    jira_api_token: str = Form(...),
):
    r = requests.get(f"{JIRA_BASE_URL}/rest/api/3/myself", auth=(email, jira_api_token))

    if r.status_code == 200:
        session_id = create_session(email, jira_api_token)
        redirect_resp = RedirectResponse(url="/menu", status_code=302)
        redirect_resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            max_age=SESSION_EXPIRE_SECONDS,
            path="/",  # add cookie in root dir
        )
        return redirect_resp
    else:
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=302)


# GET /logout
@router.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    user_email = "Unknown user"
    if session_id:
        user_data = redis_client.get(session_id)
        if user_data:
            data_dict = json.loads(user_data)
            user_email = data_dict.get("user_email")
        redis_client.delete(session_id)  # delete redis session

    # add logout message
    message = f"{user_email} has logged out"
    logger.info(message)
    response = templates.TemplateResponse(
        "login.html", {"request": request, "message": message}
    )
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
