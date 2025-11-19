import os

# session
SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", 3600))

# redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# jira
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://de101.atlassian.net/")
JIRA_ADMIN_GROUP = os.getenv("JIRA_BASE_URL", "jira-admins-de101")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "DATA")
JIRA_MAX_RESULTS = 500
JIRA_TICKETS_PER_PAGE = 10

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = 3306
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "data_request")
ALLOW_LOCAL_INFILE = True

# file related
FILE_PATH = "/app/file_path/"
SAMPLE_NUM_USERS = 1000000
CHUNK_SIZE = 100000
SAMPLE_DATA_PATH = "data/users.csv"

# slack
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "secret")

# logging configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE_NAME = "app.log"
LOG_FORMATER = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 30  # keep 30 backup log files (1 month)
