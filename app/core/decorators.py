# app/core/decorators.py
import inspect
import json
from functools import wraps

from fastapi.responses import RedirectResponse

from app.core.logger import logger
from app.core.redis_client import redis_client


# checks whether user session exists
def is_logged_in(func):
    """
    if user_session no longer exists, automaticaly redirects to login page
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            logger.error("Request parameter is required")
            raise ValueError("Request parameter is required")
        # check if session_id exists
        session_id = request.cookies.get("session_id")
        if not session_id:
            logger.error("session_id is missing or session has expired")
            return RedirectResponse(url="/login?msg=Session+expired", status_code=302)

        # check if session is valid
        session_value = redis_client.get(session_id)
        if not session_value:
            return None

        user_email = json.loads(session_value).get("user_email")
        logger.info(f"user logged_in: {user_email}")
        if not user_email:
            return RedirectResponse(url="/login?msg=Session+expired", status_code=302)
        # if session is valid, proceed to the original function
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)  # async 함수면 await
        else:
            return func(*args, **kwargs)

    return wrapper
