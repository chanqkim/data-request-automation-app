from mysql.connector import connect

from app.config import (
    ALLOW_LOCAL_INFILE,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


# retrun mysql conn object
def get_db_connection():
    return connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        allow_local_infile=ALLOW_LOCAL_INFILE,
    )
