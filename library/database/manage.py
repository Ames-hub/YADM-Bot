from sqlalchemy import create_engine, select, insert, Column, Integer, BigInteger, TEXT, TIMESTAMP, BOOLEAN, text, DateTime, FLOAT, inspect
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
    whistleblower = Column(TEXT, nullable=False)

class guild_text_automod_settings(Base):
    __tablename__ = "guild_text_automod_settings"
    
    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    penalty_delete_message = Column(BOOLEAN, nullable=False, default=False)
    penalty_warn_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_duration = Column(BigInteger, nullable=False, default=-1)  # -1 = Permanent
    penalty_kick_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_ban_member = Column(BOOLEAN, nullable=False, default=False)
    ban_duration = Column(Integer, nullable=False, default=86400)  # 1 day
    ban_msg_purgetime = Column(Integer, nullable=False, default=600)  # 10 minutes
    sim_check_threshold = Column(FLOAT, nullable=False, default=0.80)
    do_cooldown = Column(BOOLEAN, nullable=False, default=True)
    announce_infraction = Column(BOOLEAN, nullable=False, default=True)
    announce_kick = Column(BOOLEAN, nullable=False, default=True)
    announce_ban = Column(BOOLEAN, nullable=False, default=True)
    use_preset_swears_list = Column(BOOLEAN, nullable=False, default=True)
    use_preset_slurs_list = Column(BOOLEAN, nullable=False, default=True)
    use_preset_lessnsfw_list = Column(BOOLEAN, nullable=False, default=False)
    use_preset_hardnsfw_list = Column(BOOLEAN, nullable=False, default=True)

class guild_text_automod_text_checks(Base):
    __tablename__ = "guild_text_automod_text_checks"
    
    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    equality_check = Column(BOOLEAN, nullable=False, default=True)
    symbol_check = Column(BOOLEAN, nullable=False, default=True)
    collapsed_check = Column(BOOLEAN, nullable=False, default=True)
    spacehack_check = Column(BOOLEAN, nullable=False, default=False)
    letter_stitch_check = Column(BOOLEAN, nullable=False, default=False)
    reverse_check = Column(BOOLEAN, nullable=False, default=False)
    similarity_check = Column(BOOLEAN, nullable=False, default=False)
    syntactic_analysis = Column(BOOLEAN, nullable=False, default=False)

class guild_spam_automod_settings(Base):
    __tablename__ = "guild_spam_automod_settings"
    
    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    penalty_delete_message = Column(BOOLEAN, nullable=False, default=False)
    penalty_warn_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_duration = Column(BigInteger, nullable=False, default=120)  # -1 = Permanent, 120 is 2 mins
    penalty_kick_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_ban_member = Column(BOOLEAN, nullable=False, default=False)
    ban_duration = Column(Integer, nullable=False, default=86400)  # 1 day
    ban_msg_purgetime = Column(Integer, nullable=False, default=600)  # 10 minutes
    do_cooldown = Column(BOOLEAN, nullable=False, default=True)
    announce_infraction = Column(BOOLEAN, nullable=False, default=True)
    announce_kick = Column(BOOLEAN, nullable=False, default=True)
    announce_ban = Column(BOOLEAN, nullable=False, default=True)

class guild_images_automod_settings(Base):
    __tablename__ = "guild_images_automod_settings"
    
    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    penalty_delete_message = Column(BOOLEAN, nullable=False, default=False)
    penalty_warn_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_mute_duration = Column(BigInteger, nullable=False, default=-1)  # -1 = Permanent
    penalty_kick_member = Column(BOOLEAN, nullable=False, default=False)
    penalty_ban_member = Column(BOOLEAN, nullable=False, default=False)
    ban_duration = Column(Integer, nullable=False, default=86400)  # 1 day
    ban_msg_purgetime = Column(Integer, nullable=False, default=600)  # 10 minutes, >0 is no deletion
    do_cooldown = Column(BOOLEAN, nullable=False, default=True)
    announce_infraction = Column(BOOLEAN, nullable=False, default=True)
    announce_kick = Column(BOOLEAN, nullable=False, default=True)
    announce_ban = Column(BOOLEAN, nullable=False, default=True)

class guild_automod_settings(Base):
    __tablename__ = "guild_automod_settings"

    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    do_image_filtering = Column(BOOLEAN, nullable=False, default=False)
    do_filter_spam = Column(BOOLEAN, nullable=False, default=False)
    do_text_scan = Column(BOOLEAN, nullable=False, default=False)
    muted_role_id = Column(BigInteger, nullable=True, default=None)

class guild_imagescan_threshold(Base):
    __tablename__ = "guild_imagescan_threshold"

    guild_id = Column(BigInteger, nullable=False, primary_key=True)
    threshold = Column(FLOAT, nullable=False, default=0.95)

class guild_custom_wordlist(Base):
    __tablename__ = "guild_custom_wordlist"

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    word = Column(TEXT, nullable=False)
    blacklisted = Column(BOOLEAN, nullable=False, default=True)  # If false, then its a whitelisted word.

class mute_record(Base):
    __tablename__ = "mute_records"

    case_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    scheduled_unmute = Column(Integer, nullable=False, default=-1)  # -1 is permanent
    active = Column(BOOLEAN, nullable=False, default=True)
    reason = Column(TEXT, nullable=False)
    moderator_id = Column(BigInteger, nullable=False)
    is_cooldown = Column(BOOLEAN, nullable=False, default=False)

class automod_nsfw_scan_feedback(Base):
    __tablename__ = "automod_nsfw_scan_feedback"

    msg_id = Column(BigInteger, primary_key=True, nullable=False)
    msg_creation_date = Column(DateTime, nullable=False)
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
    time = Column(DateTime, nullable=False)

class scanned_image_list(Base):
    __tablename__ = "image_whitelists"

    image_hash = Column(TEXT, primary_key=True)
    whitelisted = Column(BOOLEAN, nullable=False)

class guild_welcome_msg(Base):
    __tablename__ = "guild_welcome_messages"

    guild_id = Column(BigInteger, primary_key=True)
    message = Column(TEXT, default="Please give <mention> them a warm welcome!")

class guild_welcomer_enabled(Base):
    __tablename__ = "guild_welcomer_enabled"

    guild_id = Column(BigInteger, primary_key=True)
    enabled = Column(BOOLEAN, default=False)

class guild_welcomer_channel(Base):
    __tablename__ = "guild_welcomer_channels"

    guild_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger)

class guild_join_role(Base):
    __tablename__ = "guild_joinroles"

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, nullable=False, unique=True)

class guild_audit_log_entry(Base):
    __tablename__ = "guild_audit_logs"
    
    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    entry_text = Column(TEXT, nullable=False)

class guild_log_channel(Base):
    __tablename__ = "guild_log_channels"
    
    guild_id = Column(BigInteger, primary_key=True)
    channel = Column(BigInteger, nullable=True)

class guild_ban_record(Base):
    __tablename__ = "guild_ban_records"
    
    case_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    banned_id = Column(BigInteger, nullable=False)
    moderator_id = Column(BigInteger, nullable=False)
    time_to_unban = Column(DateTime, nullable=False)
    reason = Column(TEXT, nullable=False)

class reaction_role_group(Base):
    __tablename__ = "reaction_role_groups"

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=True)
    channel_id = Column(BigInteger, nullable=False)
    embed_title = Column(TEXT, nullable=False)
    embed_desc = Column(TEXT, nullable=False)

class reaction_role_item(Base):
    __tablename__ = "reaction_role_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=True)
    
    trigger_emoji_id = Column(TEXT, nullable=False)
    trigger_emoji_name = Column(TEXT, nullable=False)
    is_animated = Column(BOOLEAN, nullable=False)

    reaction_role_id = Column(BigInteger, nullable=False)
    allow_unreact = Column(BOOLEAN, nullable=False, default=True)
    description = Column(TEXT, nullable=True)

class observation_entry(Base):
    __tablename__ = "observation_logs"
    msg_id = Column(BigInteger, nullable=False, primary_key=True)
    username = Column(TEXT, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    msg_content = Column(TEXT, nullable=False)
    bot_response = Column(TEXT, nullable=True)
    reeval_date = Column(DateTime, nullable=True)

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
    log_msg = "Working on building a PostgreSQL DB With Docker."
    print(log_msg)
    logging.info(log_msg)

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
        exit(0)

    logging.info("Docker PostgreSQL ready.")
    return True

def wait_for_db(url: str, retries: int = 30, delay: int = 2) -> bool:
    global engine, SessionLocal

    if settings.get.db_port() is None and settings.get.prod_mode() is True:  # If this is none, the rest are also likely None.
        if settings.get.allow_docker_fallback():
            logging.info("Postgres Fallback DB Initiated: Creating docker DB using image 'postgres'")
            create_docker_postgres()
            url = postgres_url(settings.getgroup.db_details())
        else:
            error = (
                "Error! We are not allowed to make a fallback DB, and no externally configured DB is set while on Production mode. "
                "To fix this, please set the following variable in settings: allow_docker_fallback = True OR set a DB"
            )
            print(error)
            raise ConnectionAbortedError(error)

    logging.info("DB: Creating engine")

    engine = create_engine(url, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)

    logging.info("DB: Beginning to attempt to connect to PostgreSQL database.")
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("Database connection successful.")
            return True
        except OperationalError as err:
            logging.debug(f"DB attempt {i+1}/{retries} failed: {err}", exc_info=err)
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
        logging.info("Sqlite Database ready and schema upgraded.")
        return True

    # postgres (for prod)
    logging.info("Production mode: using PostgreSQL.")

    db_details = settings.getgroup.db_details()
    url = postgres_url(db_details)

    if not wait_for_db(url):
        logging.error("PostgreSQL connection failed.")
        return False

    Base.metadata.create_all(bind=engine)
    logging.info("PostgreSQL Database ready and schema upgraded.")
    return True

def transfer_database(source_url: str, dest_url: str, chunk_size: int = 1000, echo: bool = False):
    """
    Copy data from source DB to destination DB using SQLAlchemy models (Base.metadata).
    Tables are created in destination using Base.metadata, so SQLite compatibility is ensured.
    """

    # Engines
    source_engine = create_engine(source_url, echo=echo, future=True)
    dest_engine = create_engine(dest_url, echo=echo, future=True)

    # Create destination tables (SQLite-compatible)
    Base.metadata.create_all(bind=dest_engine)

    # Sessions
    SourceSession = sessionmaker(bind=source_engine, future=True)
    DestSession = sessionmaker(bind=dest_engine, future=True)

    with SourceSession() as src, DestSession() as dst:
        for table in Base.metadata.sorted_tables:
            logging.info(f"Transferring table: {table.name}")
            offset = 0
            while True:
                # Fetch rows in chunks
                rows = src.execute(select(table).offset(offset).limit(chunk_size)).mappings().all()
                if not rows:
                    break

                # Insert into destination
                dst.execute(insert(table), rows)
                dst.commit()
                offset += chunk_size

    logging.info("Database transfer complete.")
    return True

def modernize() -> None:
    """
    Auto-sync database schema:
    - Creates missing tables
    - Adds missing columns
    - Does NOT remove or modify existing columns
    Safe for SQLite and PostgreSQL.
    """

    global engine

    if engine is None:
        initialize()

    inspector = inspect(engine)

    existing_tables = set(inspector.get_table_names())
    model_tables = Base.metadata.tables

    with engine.begin() as conn:
        for table_name, table in model_tables.items():
            if table_name not in existing_tables:
                logging.info(f"Creating missing table: {table_name}")
                table.create(bind=conn)
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

            for column in table.columns:
                if column.name not in existing_columns:
                    logging.info(f"Adding missing column '{column.name}' to '{table_name}'")

                    # Compile column type for current dialect
                    column_type = column.type.compile(engine.dialect)

                    nullable = "NULL" if column.nullable else "NOT NULL"

                    default_clause = ""
                    if column.default is not None and hasattr(column.default, "arg"):
                        default_value = column.default.arg
                        if isinstance(default_value, str):
                            default_clause = f" DEFAULT '{default_value}'"
                        else:
                            default_clause = f" DEFAULT {default_value}"

                    sql = (
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column.name} {column_type} "
                        f"{nullable}{default_clause}"
                    )

                    conn.execute(text(sql))

    logging.info("Database schema auto-synchronized.")