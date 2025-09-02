import os

SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", 3600))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://de101.atlassian.net/")
