from library.settings import get, set
import modules, essentials
import datetime
import logging
import asyncio
import dotenv
import sys
import os

logging.basicConfig(
    filename=f"logs/{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if bot_token:
            set.bot_token(bot_token)
            print("Detected .env file, loading bot token from there.\n\n")

        bot_name = os.getenv("BOT_NAME", "").strip()
        if bot_name:
            set.bot_name(bot_name)
            print(f"Detected .env file, loading bot name '{bot_name}' from there.\n\n")

        prod_mode = os.getenv("PROD_MODE", "").strip().lower()
        if prod_mode in ("y", "yes", "true", "1"):
            set.prod_mode(True)
            print("Detected .env file, enabling production mode from there.\n\n")
        elif prod_mode in ("n", "no", "false", "0"):
            set.prod_mode(False)
            print("Detected .env file, disabling production mode from there.\n\n")

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

    print("Thank you for using Railway Bot!")
    if not bot_token:
        print("To get started, please enter your Discord bot token.")
        token = input(">>> ").strip()
        set.bot_token(token)
        print("Bot token saved.\n\n")

    if not bot_name:
        print("What's the bot's name?")
        while True:
            name = input(">>> ").strip()
            if len(name) > 0:
                set.bot_name(name)
                break
            else:
                print("Name cannot be blank.")
                continue
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

# ----- BOT ENVIRONMENT SETUP SECTION -----

from library.postgre import manage as pg_manage
db_init_success = pg_manage.initialize()
if db_init_success:
    pg_manage.modernize()
else:
    print("Error: Unable to initialize the database connection. Please check your settings and ensure the database is reachable.")
    raise ConnectionError("Database initialization failed.")

# Always check to see if a DB can be reached or made.
if get.allow_docker_fallback() is False and not get.db_host():
    logging.error("No external DB configured and Docker fallback is disabled. Cannot proceed.")
    print("Error: Without an external DB configured or Docker fallback enabled, the bot will not function properly.")
    print("Please re-run the setup and configure a database or allow Docker fallback.\n\n")
    print("To rerun the setup, delete the settings.json file and restart the bot.")
    raise ValueError("No DB configured and Docker fallback disabled.")

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
    logging.warning("Bot name is not set. Using default 'Railway'.")
    set.bot_name("Railway")

# ----- BOT SETUP SECTION -----
from library.botapp import botapp, client
import hikari

@botapp.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    # Load any extensions
    await client.load_extensions_from_package(modules)
    await client.load_extensions_from_package(essentials)
    # Start the bot - make sure commands are synced properly
    await client.start()

@botapp.listen(hikari.ShardReadyEvent)
async def on_shard_ready(event: hikari.ShardReadyEvent) -> None:
    msg = f"Shard {event.shard.id} is ready and connected to Discord!"
    print(msg)
    logging.info(msg)

try:
    if os.name != "nt":
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    botapp.run(
        shard_count=15 if prod_mode else 1
    )
except KeyboardInterrupt:
    print("Interrupt signal received, shutting down...")
    exit(0)
except hikari.ForbiddenError as err:
    print("Error: Discord has forbidden access. Check bot token. details:", err)
    exit(1)
