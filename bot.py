from library.settings import get, set, getgroup, setgroup
from library import datastore as ds
from library import benchmark as bm
import essentials
import datetime
import logging
import asyncio
import dotenv
import sys
import os

bm.benchmark("Program start")

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=f"logs/{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if os.name == "nt":
    set.ai_vision_enabled(False)  # No AI Support for Windows.
    logging.info("AI Vision has been disabled due to the OS being Windows.")

bm.benchmark("Logging initialized")

if "--backup" in sys.argv and "--restore" in sys.argv:
    msg = (
        "\n\n----> WARNING <----\nThis is not an advanced backup system.\n"
        "Please do not do unusual things like calling restore and backup at the same time.\n\n"
    )
    print(msg)
    logging.warning(msg)
    exit(1)

# Check if "--backup" is in the call arg
if "--backup" in sys.argv:
    if get.prod_mode() is False:
        raise RuntimeError("This bot is not in production mode, and does not have a DB to backup.")

    from library.database import manage as dbman    
    try:
        success = dbman.transfer_database(source_url=dbman.postgres_url(getgroup.db_details()), dest_url=dbman.sqlite_url())
    except Exception as err:
        logging.basicConfig(
            filename="error.log",
            level=logging.ERROR,
        )

        print("Uh oh! Backup error! See logs.")
        logging.error("Error backing up!", exc_info=err)
        exit(2)

    if success:
        print("DB Backup completed! Exitting.")
        logging.info("DB Backup completed! Exitting.")
    else:
        print("Failed to backup DB!")
        logging.warning("Failed to backup DB!")
    exit(0)
elif "--restore" in sys.argv:
    from library.database import manage as dbman

    input("We're about to restore your PG Database from a backup. Please put the data.sqlite backup file in the root directory and press enter.")

    db_init_success = dbman.initialize()
    if db_init_success:
        try:
            success = dbman.transfer_database(source_url=dbman.sqlite_url(), dest_url=dbman.postgres_url(getgroup.db_details()))
        except Exception as err:
            logging.basicConfig(
                filename="error.log",
                level=logging.ERROR,
            )

            print("During this, you may see many errors about an sqlalchemy.exc.OperationalError. Ignore them. It's just the DB trying to connect.")

            print("Uh oh! Backup restoration error! See logs.")
            logging.error("Error backing up!", exc_info=err)
            exit(2)
        if success:
            print("DB restoration completed! Exitting.")
            logging.info("DB Restoration Completed! Exitting.")
        else:
            print("DB restoration Failed! Exitting.")
            logging.warning("DB Restoration Failed! Exitting.")
    exit(0)
elif "--setup-db" in sys.argv:
    from library.database import manage as pg_manage
    print("DB Setup beginning. Details for your pre-existing postgre SQL database required.")
    username = input("Username: >>> ")
    password = input("Password: >>> ")
    db_name = input("DB Name: >>> ")
    db_host = input("DB Host: >>> ")
    db_port = input("DB Port: >>> ")
    print("We will now attempt to connect to this database.")
    pg_manage.wait_for_db(
        pg_manage.postgres_url({
            "user": username,
            "password": password,
            "host": db_host,
            "port": db_port,
            "dbname": db_name
        }),
        ever_create_db=False
    )
    setgroup.db_details({
        "user": username,
        "password": password,
        "host": db_host,
        "port": db_port,
        "dbname": db_name
    })
    set.prefer_mainydb(False)
    print("DB Setup confirmed. Saved.")
    exit(0)
elif "--enable-webui-cmds" in sys.argv:
    print("To enable /dashboard command for the WebUI, please enter the Hostname of the WebUI.")
    print("This would be whatever address you use to connect to the WebUI, whether that be http://192.168.1.123:8040 or https://yourbot.com")
    hostname = input(">>> ")
    if not hostname.startswith("http"):
        print("Bad input: must be a full link. Missing if its HTTPS or HTTP")
        exit(0)
    elif not "." in hostname:
        print("Bad input: Missing domain (eg, .com)")
        exit(0)
    set.webui_hostname(hostname)
    print("")
    exit(0)

# ----- INITIAL SETUP SECTION -----
if not get.bot_token():
    bot_token = None
    bot_name = None
    prod_mode = None
    allow_docker_fallback = None
    db_host = None
    db_user = None
    db_password = None
    db_name = None
    db_port = None

    if os.path.exists(".env"):
        dotenv.load_dotenv(".env")
        prod_mode = os.getenv("PROD_MODE", "").strip().lower()
        if prod_mode in ("y", "yes", "true", "1"):
            set.prod_mode(True)
            print("Detected .env file, enabling production mode from there.\n\n")
        elif prod_mode in ("n", "no", "false", "0"):
            set.prod_mode(False)
            print("Detected .env file, disabling production mode from there.\n\n")

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if bot_token:
            set.bot_token(bot_token)
            print("Detected .env file, loading bot token from there.\n\n")

        primary_maintainer = os.getenv("PRIMARY_MAINTAINER", "")
        if primary_maintainer:
            set.primary_maintainer(int(primary_maintainer))
            print(f"Detected .env file, loading primary maintainer '{primary_maintainer}' from there.")

        bot_name = os.getenv("BOT_NAME", "").strip()
        if bot_name:
            set.bot_name(bot_name)
            print(f"Detected .env file, loading bot name '{bot_name}' from there.\n\n")

        allow_docker_fallback = os.getenv("ALLOW_DOCKER_FALLBACK", "").strip().lower()
        if allow_docker_fallback in ("y", "yes", "true", "1"):
            set.allow_docker_fallback(True)
            print("Detected .env file, enabling Docker fallback from there.\n\n")
        elif allow_docker_fallback in ("n", "no", "false", "0"):
            set.allow_docker_fallback(False)
            print("Detected .env file, disabling Docker fallback from there.\n\n")

        db_host = os.getenv("DB_HOST", "").strip()
        db_user = os.getenv("DB_USER", "").strip()
        db_password = os.getenv("DB_PASSWORD", "").strip()
        db_name = os.getenv("DB_NAME", "").strip()
        db_port = os.getenv("DB_PORT", "").strip()
        if db_host and db_user and db_password and db_name and db_port:
            set.db_host(db_host)
            set.db_username(db_user)
            set.db_password(db_password)
            set.db_name(db_name)
            if db_port.isdigit():
                set.db_port(int(db_port))
            print("Detected .env file, loading database configuration from there.\n\n")

    print("Thank you for using YADM Bot!")
    if not bot_token:
        print("To get started, please enter your Discord bot token.")
        token = input(">>> ").strip()
        set.bot_token(token)
        print("Bot token saved.\n\n")

    print("Great! Now, would you like to use a separate discord bot token for when you are testing the bot? (y/n)")
    use_debug_token = input(">>> ") == "y"
    if use_debug_token:
        print("Please enter your DEBUG discord bot token.")
        debug_token = input(">>> ")
        set.nonprod_bot_token(debug_token)
    else:
        set.nonprod_bot_token(token)  # Set both as the same

    if not bot_name:
        print("What's the bot's name? (Default: Nodeus)")
        while True:
            name = input(">>> ").strip()
            if len(name) > 0:
                set.bot_name(name)
                break
            else:
                name = "Nodeus"
                set.bot_name(name)
        print(f"Great! Your bot's name is set to: {name}\n\n")

    if prod_mode is None:
        print("\nNext, would you like to enable production mode? (y/n)")
        print("This means we will be more likely to enforce stricter settings for security and stability.")
        prod_mode = input(">>> ").strip().lower()
        if prod_mode in ("y", "yes"):
            set.prod_mode(True)
            print("Production mode enabled.\n\n")
        else:
            set.prod_mode(False)
            print("Production mode disabled. Running in development mode.\n\n")

    if allow_docker_fallback is None:
        print("Do you want to allow me to make a local Docker PostgreSQL database in the case of a fallback? (y/n)")
        print("This will allow the bot to keep running even if the external DB is unreachable, but requires Docker to be installed and we'd need permissions for it.")
        allow_docker_fallback = input(">>> ").strip().lower()
        if allow_docker_fallback in ("y", "yes", ""):  # Default to yes
            set.allow_docker_fallback(True)
            print("Docker fallback enabled.\n\n")
        else:
            set.allow_docker_fallback(False)
            print("Docker fallback disabled.\n\n")

    if not db_host or not db_user or not db_password or not db_name or not db_port:
        print("Would you like to configure an external PostgreSQL database now? (y/n)")
        configure_db = input(">>> ").strip().lower()
        if configure_db in ("y", "yes"):
            db_host = input("Enter DB host: ").strip()
            db_port = input("Enter DB port (default 5432): ").strip()
            db_name = input("Enter DB name: ").strip()
            db_user = input("Enter DB username: ").strip()
            db_password = input("Enter DB password: ").strip()
            set.db_host(db_host)
            set.db_port(int(db_port) if db_port.isdigit() else 5432)
            set.db_name(db_name)
            set.db_username(db_user)
            set.db_password(db_password)
            print("Database configuration saved.\n\n")
        else:
            print("Skipping external DB configuration. Relying on Docker fallback if needed.\n\n")

    if not allow_docker_fallback and not db_host:
        print("Error: Without an external DB configured or Docker fallback enabled, the bot will not function properly.")
        print("Please re-run the setup and configure a database or allow Docker fallback.\n\n")
        print("To rerun the setup, delete the settings.json file and restart the bot.")
        raise ValueError("No DB configured and Docker fallback disabled.")

bm.benchmark("Pre-launch checks completed")

# ----- BOT ENVIRONMENT SETUP SECTION -----

if __name__ == "__main__":
    from library.database import manage as pg_manage
    db_init_success = pg_manage.initialize()
    if db_init_success:
        pg_manage.modernize()
    else:
        print("Error: Unable to initialize the database connection. Please check your settings and ensure the database is reachable.")
        raise ConnectionError("Database initialization failed.")

# Always check to see if a DB can be reached or made.
if (get.allow_docker_fallback() is False and not get.db_host()) and get.prod_mode():
    logging.error("No external DB configured and Docker fallback is disabled. Cannot proceed.")
    print("Error: Without an external DB configured or Docker fallback enabled, the bot will not function properly.")
    print("Please re-run the setup and configure a database or allow Docker fallback.\n\n")
    print("To rerun the setup, delete the settings.json file and restart the bot.")
    raise ValueError("No DB configured and Docker fallback disabled.")
else:
    logging.warning("Nodeus is running with Sqlite3")

prod_mode = get.prod_mode()

if prod_mode:
    logging.info("Running in production mode.")
    # Ensure that -O or -OO flags are used
    if not (hasattr(sys, 'flags') and (sys.flags.optimize >= 1)):
        logging.warning("This bot is in production mode and is being told to run without optimizations! Exitting.")
        print("Error: Production mode requires Python to be run with optimizations enabled (use -O or -OO when calling Python. Eg, python3.13 -O app.py).")
        raise ValueError("Production mode requires Python optimizations.")

    if not get.bot_name():
        logging.error("Bot name is not set in production mode! Exitting.")
        print("Error: Bot name must be set in production mode. Please re-run the setup.")
        raise ValueError("Bot name not set in production mode.")

if not get.bot_name() and not prod_mode:
    logging.warning("Bot name is not set. Using default 'Nodeus'.")
    set.bot_name("Nodeus")

bm.benchmark("Bot environment estimation setup completed.")

# ----- BOT SETUP SECTION -----
from library.botapp import botapp, client
import importlib
import hikari

@botapp.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    modules_dir = "modules"

    for root, dirs, files in os.walk(modules_dir):
        if "__init__.py" not in files:
            if "__pycache__" in root:
                continue  # Skip pycache
            logging.info(f"Skipping {root} as it does not have an __init__.py")
            continue  # skip non-packages

        # Convert file system path to Python package path
        package_path = root.replace(os.path.sep, ".")
        package = importlib.import_module(package_path)
        await client.load_extensions_from_package(package)

    # Load essentials separately
    await client.load_extensions_from_package(essentials)
    await client.start()

@botapp.listen(hikari.ShardReadyEvent)
async def on_shard_ready(event: hikari.ShardReadyEvent) -> None:
    msg = f"Shard {event.shard.id} is ready and logged in as \"{event.my_user.username}\" to Discord!"
    print(msg)
    logging.info(msg)
    ds.d["myid"] = event.my_user.id

from library.other import get_os_name

# ------- ds.d configuration ------- #
ds.d["time_at_boot"] = datetime.datetime.now()
ds.d["myid"] = None  # Set in the on_shard_ready func.
ds.d["guild_name_cache"] = {}  #  Used by the "handle_guilty" func to avoid spamming the API for guild name requests.
ds.d["PRIMARY_MAINTAINER"] = get.primary_maintainer()  # Used to enable specific features.
ds.d["guild_owner_ids_cache"] = {}
ds.d["filter_exemptions"] = {}  # People who are not looked at by the automod. Assigned by admins, and its per-guild.
ds.d["spam_cache"] = {}
ds.d["spam_punish_cache"] = {}  # Cache to track when users were last punished for spam, to avoid punishing them multiple times in a short period
ds.d["bad_word_list_cache"] = {}
ds.d["rr_role_names_cache"] = {}

try:
    logging.info(f"OS Detected: {get_os_name()}")

    if os.name != "nt":
        # More efficient than usual event loop policy
        import uvloop
        logging.info(f"Using linux uvloop")
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)

    bm.benchmark("All pre-flight checks completed, initalization of bot commencing.")
    botapp.run(
        shard_count=5 if prod_mode else 1
    )
except KeyboardInterrupt:
    print("Interrupt signal received, shutting down...")
    exit(0)
except hikari.ForbiddenError as err:
    print("Error: Discord has forbidden access. Check bot token. details:", err)
    exit(1)
