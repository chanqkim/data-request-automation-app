import os
from datetime import datetime, timezone

from mysql.connector import connect

from app.config import (
    ALLOW_LOCAL_INFILE,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)
from app.core.logger import logger


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


# save data-extraction log to mysql
def save_log_to_mysql(
    extractor_id: str,
    ticket_key: str,
    file_path: str,
):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                    INSERT INTO data_extraction_history (
                        extractor_id, ticket_key, file_name, file_path,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
            # 현재 시점 timestamp
            now = datetime.now(timezone.utc)

            cursor.execute(
                sql,
                (
                    extractor_id,
                    ticket_key,
                    os.path.basename(file_path) if file_path else None,
                    file_path,
                    now,  # created_at
                ),
            )
        conn.commit()
        logger.info(f"[Jira {ticket_key}] data-extraction log has been saved!: ")

    except Exception as e:
        logger.error(f"[MySQL ERROR] Failed to save log: {e}")
