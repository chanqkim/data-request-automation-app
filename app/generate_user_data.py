import csv
import os
import random

from faker import Faker

from app.config import SAMPLE_DATA_PATH, SAMPLE_NUM_USERS
from app.core.db_connection import get_db_connection
from app.core.logger import logger


# truncate string to meet mysql max length
def truncate(value, max_len):
    return value[:max_len] if value else value


# format datetime to remove microseconds for mysql compatibility
def format_datetime(dt):
    return dt.replace(microsecond=0)


# create sample user_data that will be used for data extraction
def create_sample_data():
    fake = Faker()
    # add seed to have consistent random sample data
    fake.seed_instance(4321)

    # options for random values
    genders = ["M", "F", "Other"]
    roles = ["user", "admin", "vendor"]
    devices = ["web", "mobile"]
    oses = ["Windows 10", "Windows 11", "macOS 14", "iOS 17", "Android 13"]

    with open(SAMPLE_DATA_PATH, "w", newline="", encoding="utf-8") as csvfile:
        logger.info(f"Creating sample data, path:{SAMPLE_DATA_PATH}")
        writer = csv.writer(csvfile)
        # csv header list
        writer.writerow(
            [
                "username",
                "password_hash",
                "email",
                "first_name",
                "last_name",
                "gender",
                "birth_date",
                "country",
                "city",
                "languages",
                "date_joined",
                "is_active",
                "user_role",
                "created_at",
                "updated_at",
                "last_login_at",
                "device_type",
                "os",
            ]
        )

        # generate random sample data
        cnt = 0
        for _ in range(SAMPLE_NUM_USERS):
            gender = random.choice(genders)
            first_name = (
                fake.first_name_male()
                if gender == "M"
                else fake.first_name_female()
                if gender == "F"
                else fake.first_name()
            )
            last_name = fake.last_name()
            username = fake.unique.user_name() + str(random.randint(1, 1000))
            email = fake.unique.free_email()
            password_hash = "hashedpwd" + str(random.randint(1, 999999))
            birth_date = fake.date_of_birth(minimum_age=18, maximum_age=80)
            country = fake.country()
            city = fake.city()
            languages = fake.language_code()
            is_active = random.choice([True, False])
            user_role = random.choice(roles)
            created_at = format_datetime(fake.date_time_this_decade())
            updated_at = format_datetime(
                fake.date_time_between(start_date=created_at)
            )  # date after created_at
            last_login_at = format_datetime(
                fake.date_time_between(start_date=created_at, end_date=updated_at)
            )
            device_type = random.choice(devices)
            os_choice = random.choice(oses)

            writer.writerow(
                [
                    username,
                    password_hash,
                    email,
                    first_name,
                    last_name,
                    gender,
                    birth_date,
                    country,
                    city,
                    languages,
                    is_active,
                    user_role,
                    created_at,
                    updated_at,
                    last_login_at,
                    device_type,
                    os_choice,
                ]
            )
            cnt = cnt + 1
            if cnt % 100000 == 0:
                logger.info(f"{cnt} sample data has been created")


# insert sample data to database
def insert_sample_data_to_db():
    logger.info("Inserting sample data into users table")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # import sample csv data to users table
        load_sql = f"""
        LOAD DATA LOCAL INFILE '{os.path.abspath(SAMPLE_DATA_PATH)}'
        INTO TABLE users
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (username, password_hash, email, first_name, last_name, gender,
        birth_date, country, city, languages, is_active,
        user_role, created_at, updated_at, last_login_at, device_type, os);
        """

        cursor.execute(load_sql)
        cursor.execute("SHOW WARNINGS;")

        # check warning messages
        warnings = cursor.fetchall()
        for w in warnings:
            logger.info(w)

        # check how many rows were inserted
        logger.info(f"data insertion compolete, data count: {cursor.rowcount}")

        if cursor.rowcount != SAMPLE_NUM_USERS:
            logger.error(
                f"Warning: Expected {SAMPLE_NUM_USERS} rows, but inserted {cursor.rowcount} rows."
            )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.info(f"Raised Exception: {e}")


if __name__ == "__main__":
    # create_sample_data()
    insert_sample_data_to_db()
