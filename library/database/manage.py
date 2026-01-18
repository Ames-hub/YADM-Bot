from sqlalchemy import create_engine, Column, Integer, BigInteger, TEXT, TIMESTAMP, BOOLEAN, text, CheckConstraint, Time
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from library.settings import get
from library import settings
from pathlib import Path
import subprocess
import logging
import secrets
import string
import time


prod_mode = get.prod_mode()

# SQLite file location (non-prod only)
SQLITE_PATH = Path("./local.db")

Base = declarative_base()
engine = None
SessionLocal = None

class member_violations(Base):
    """A Record of all the times guild members broke the rules."""
    __tablename__ = "member_violations"

    reporter_id = Column(BigInteger, nullable=False)
    offender_id = Column(BigInteger, nullable=False)
    time = Column(TIMESTAMP, nullable=False)
    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    violation = Column(TEXT, nullable=False)
    automated = Column(BOOLEAN, nullable=False)

class guild_automod_settings(Base):
    __tablename__ = "guild_automod_settings"

    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    text_filter_level = Column(Integer, nullable=False, default=1)
    penalty_delete_message = Column(BOOLEAN, nullable=False, default=True)
    penalty_warn_member = Column(BOOLEAN, nullable=False, default=True)
    penalty_mute_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_duration = Column(BigInteger, nullable=False, default=-1)  # -1 = Permanent
    penalty_kick_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_ban_member = Column(BOOLEAN, nullable=False, default=False)
    ban_msg_purgetime = Column(Integer, nullable=False, default=600)  # 10 minutes
    muted_role_id = Column(BigInteger, nullable=True, default=None)
    __table_args__ = (
        # Enforce it to be 1, 2 or 3. Higher = more intense checking.
        CheckConstraint('text_filter_level >= 1 AND text_filter_level <= 3', name='ck_text_filter_level_range'),
    )

class guild_custom_wordlist(Base):
    __tablename__ = "guild_custom_wordlist"

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    word = Column(TEXT, nullable=False)
    blacklisted = Column(BOOLEAN, nullable=False, default=True)  # If false, then its a whitelisted word.

class mute_records(Base):
    __tablename__ = "mute_records"

    case_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    scheduled_unmute = Column(Integer, nullable=False, default=-1)  # -1 is permanent
    active = Column(BOOLEAN, nullable=False, default=True)

class automod_nsfw_scan_feedback(Base):
    __tablename__ = "automod_nsfw_scan_feedback"

    msg_id = Column(BigInteger, primary_key=True, nullable=False)
    related_img_hash = Column(TEXT, unique=True, nullable=False)
    upvote_count = Column(Integer, nullable=False, default=0)
    downvote_count = Column(Integer, nullable=False, default=0)

class guild_member_warnings(Base):
    __tablename__ = "guild_member_warnings"

    warn_id = Column(Integer, primary_key=True, autoincrement=True)
    reason = Column(TEXT, nullable=False)
    moderator_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    time = Column(Time, nullable=False)

class scanned_image_list(Base):
    __tablename__ = "image_whitelists"

    image_hash = Column(TEXT, primary_key=True)
    whitelisted = Column(BOOLEAN, nullable=False)

def get_session():
    if SessionLocal is None:
        initialize()
    return SessionLocal()

def postgres_url(details: dict) -> str:
    return (
        f"postgresql+psycopg2://"
        f"{details['user']}:{details['password']}"
        f"@{details['host']}:{details['port']}"
        f"/{details['dbname']}"
    )

def sqlite_url() -> str:
    return f"sqlite:///{SQLITE_PATH.absolute()}"

def _gen_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def create_docker_postgres(
    container_name: str = f"yadm-postgres-db",
    db_name: str = "nodeus",
    user: str = "nodeus",
    port: int = 5434,
    image: str = "postgres"
) -> bool:
    """
    Creates a Dockerized PostgreSQL instance and stores credentials in settings.
    Safe to call multiple times.
    """

    password = _gen_password()

    # Check if container already exists
    check = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )

    if container_name not in check.stdout:
        logging.info("Creating new PostgreSQL Docker container.")

        result = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "-e", f"POSTGRES_DB={db_name}",
                "-e", f"POSTGRES_USER={user}",
                "-e", f"POSTGRES_PASSWORD={password}",
                "-p", f"{port}:5432",
                image
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logging.error("Failed to start PostgreSQL container.", extra={"stderr": result.stderr})
            return False
    else:
        logging.info("PostgreSQL container already exists. Reusing it.")

    # Persist DB details
    settings.setgroup.db_details(
        {
            "host": "localhost",
            "port": port,
            "user": user,
            "password": password,
            "dbname": db_name,
        }
    )

    logging.info("PostgreSQL credentials saved to settings.")

    # Wait until Postgres responds
    url = postgres_url(settings.getgroup.db_details())
    if not wait_for_db(url):
        logging.error("PostgreSQL container started but did not become reachable.")
        return False

    logging.info("Docker PostgreSQL ready.")
    return True

def wait_for_db(url: str, retries: int = 30, delay: int = 2) -> bool:
    global engine, SessionLocal

    if settings.get.db_port() is None:  # If this is none, the rest are also likely None.
        if settings.get.allow_docker_fallback():
            logging.info("Postgres Fallback DB Initiated: Creating docker DB using image 'postgres'")
            create_docker_postgres()
        else:
            error = (
                "Error! We are not allowed to make a fallback DB, and no externally configured DB is set while on Production mode. "
                "To fix this, please set the following variable in settings: allow_docker_fallback = True"
            )
            print(error)
            raise ConnectionAbortedError(error)

    engine = create_engine(url, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)

    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("Database connection successful.")
            return True
        except OperationalError as err:
            logging.debug(f"DB attempt {i+1}/{retries} failed: {err}")
            time.sleep(delay)

    logging.error("Database never became reachable.")
    return False

def initialize() -> bool:
    """
    Initializes database based on prod_mode:
      - prod_mode = False → SQLite
      - prod_mode = True  → PostgreSQL
    """

    # sqlite (for non-prod)
    if not prod_mode:
        logging.info("Non-production mode: using SQLite.")

        url = sqlite_url()

        if not wait_for_db(url, retries=3, delay=0.5):
            logging.error("Failed to initialize SQLite.")
            return False

        Base.metadata.create_all(bind=engine)
        logging.info("SQLite database ready.")
        return True

    # postgres (for prod)
    logging.info("Production mode: using PostgreSQL.")

    db_details = settings.getgroup.db_details()
    url = postgres_url(db_details)

    if not wait_for_db(url):
        logging.error("PostgreSQL connection failed.")
        return False

    Base.metadata.create_all(bind=engine)
    logging.info("PostgreSQL database ready.")
    return True

def modernize() -> None:
    """
    Ensures all defined tables exist.
    """
    global engine

    if engine is None:
        initialize()

    Base.metadata.create_all(bind=engine)
    logging.info("Schema synchronized.")
