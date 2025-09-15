# app/core/decorators.py
from functools import wraps
from fastapi.responses import RedirectResponse
from app.core.redis_client import redis_client
import inspect
import json


# checks whether user session exists
def is_logged_in(func):
    """
    if user_session no longer exists, automaticaly redirects to login page
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if not request:
            raise ValueError("Request parameter is required")
        # check if session_id exists
        session_id = request.cookies.get("session_id")
        print(f" is_logged_in session_id: {session_id}")
        if not session_id:
            return RedirectResponse(url="/login?msg=Session+expired", status_code=302)

        # check if session is valid
        session_value = redis_client.get(session_id)
        if not session_value:
            return None

        user_email = json.loads(session_value).get("user_email")  # dict 변환
        print(f" is_logged_in user_email: {user_email}")
        if not user_email:
            return RedirectResponse(url="/login?msg=Session+expired", status_code=302)
        # 세션 유효 → 원래 함수 실행
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)  # async 함수면 await
        else:
            return func(*args, **kwargs)

    return wrapper
