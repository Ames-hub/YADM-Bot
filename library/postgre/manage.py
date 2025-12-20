from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from library import settings
from library import settings
from psycopg2 import sql
import subprocess
import psycopg2
import logging
import secrets
import string
import time


def _can_connect(details: dict) -> bool:
    try:
        conn = psycopg2.connect(**details)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        conn.close()
        print("DB connection successful.")
        return True
    except Exception as e:
        logging.debug(f"DB connection failed with details {details}: {e}")
        return False

def initialize():
    """
    Fully deterministic initializer that:
      - Tries existing DB config
      - If it fails and not in prod, spins up Docker
      - Updates settings before retrying
      - Verifies container is ACTUALLY running and accepting SQL
      - Returns True only when DB is absolutely reachable
    """

    # Always reload current settings
    db_details = settings.getgroup.db_details()
    logging.info(f"INITIALIZING DB. Current settings: {db_details}")

    # ---------------- PROD MODE ----------------
    if settings.get.prod_mode():
        logging.info("Production mode: testing external DB only.")
        if _can_connect(db_details):
            logging.info("External DB OK.")
            return True
        logging.error("Production DB connection failed.")
        return False

    # ---------------- NON-PROD MODE ----------------
    logging.info("Non-prod: testing existing DB first...")

    if _can_connect(db_details):
        logging.info("Existing local DB OK.")
        return True

    logging.warning("Local DB connection failed. Creating Dockerized PostgreSQL...")

    # ---- Check Docker ----
    try:
        docker_check = subprocess.run(["docker", "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
    except FileNotFoundError:
        logging.error("Docker is not installed.")
        return False

    if docker_check.returncode != 0:
        logging.error("Docker exists but is not usable.")
        return False

    # ---- Generate fresh DB config ----
    user = "localuser"
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    db_name = "localdb"
    port = "5433"
    container_name = "local_postgres_auto"

    logging.info("DB PASSWORD GENERATED:", password)

    new_details = {
        "dbname": db_name,
        "user": user,
        "password": password,
        "host": "127.0.0.1",
        "port": port
    }

    logging.info(f"Generated new local DB config: {new_details}")

    # Kill leftovers
    subprocess.run(["docker", "rm", "-f", container_name],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ---- Start container ----
    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "-p", f"{port}:5432",
        "-e", f"POSTGRES_USER={user}",
        "-e", f"POSTGRES_PASSWORD={password}",
        "-e", f"POSTGRES_DB={db_name}",
        "postgres:latest"
    ]

    logging.info(f"Starting container with: {cmd}")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    logging.debug(f"Docker stdout: {proc.stdout}")
    logging.debug(f"Docker stderr: {proc.stderr}")

    if proc.returncode != 0:
        logging.error(f"Failed to start Docker container: {proc.stderr.decode()}")
        return False

    # ---- Save new details IMMEDIATELY ----
    settings.setgroup.db_details(new_details)
    logging.info("Updated settings with new DB details.")

    # ---- Retry until DB is truly online ----
    for i in range(30):  # ~60 seconds total
        logging.info(f"Attempt {i+1}/30: checking local DB...")
        time.sleep(2)

        if _can_connect(new_details):
            logging.info("Local Docker PostgreSQL is READY.")
            return True
        else:
            logging.debug("DB not ready yet.")

    logging.error("Docker container started but DB never became ready.")
    return False

def modernize() -> None:
    table_dict = {
        "violations": {
            "id": "SERIAL PRIMARY KEY",
            "user_id": "BIGINT NOT NULL",
        }
    }

    DB_CONFIG = settings.getgroup.db_details()

    try:
        conn: psycopg2.extensions.connection = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur: psycopg2.extensions.cursor = conn.cursor()
    except psycopg2.OperationalError as err:
        logging.error("Unable to connect to the PostgreSQL database.", err)
        raise err

    for table_name, columns in table_dict.items():
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """, (table_name,))
        table_exist = cur.fetchone()[0]

        if table_exist:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s;
            """, (table_name,))
            existing_columns = {row[0] for row in cur.fetchall()}

            for column_name, column_props in columns.items():
                if column_name not in existing_columns:
                    try:
                        cur.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} {};")
                                    .format(
                                        sql.Identifier(table_name),
                                        sql.Identifier(column_name),
                                        sql.SQL(column_props)
                                    ))
                    except Exception as err:
                        print(f"ERROR EDITING TABLE {table_name}, ADDING COLUMN {column_name} {column_props}")
                        raise err

        else:
            columns_sql = ", ".join(
                f"{col_name} {props}" for col_name, props in columns.items()
            )

            try:
                cur.execute(sql.SQL("CREATE TABLE {} ({});")
                            .format(
                                sql.Identifier(table_name),
                                sql.SQL(columns_sql)
                            ))
            except Exception as err:
                print(f"There was a problem creating the table {table_name} with columns {columns_sql}")
                logging.error(
                    f"An error occurred while creating the table {table_name} with columns {columns_sql}",
                    err
                )
                raise err

    cur.close()
    conn.close()
