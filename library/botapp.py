from hikari.intents import Intents as HKIntents
from library.settings import get
import lightbulb
import datetime
import logging
import hikari
import dotenv
import os

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=f"logs/{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if os.path.exists('.env'):
    logging.info("Loading .env file at root directory for configuration.")
    dotenv.load_dotenv('.env')
else:
    logging.info(".env file not found project root; skipping load.")

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
BOT_TOKEN = get.bot_token()

intents_list = [HKIntents.GUILD_MESSAGES, HKIntents.GUILDS, HKIntents.MESSAGE_CONTENT]
intents = 0
for intent in intents_list:
    intents += intent

botapp = hikari.GatewayBot(
    intents=intents,
    token=BOT_TOKEN,
    logs={
        "version": 1,
        "incremental": True,
        "loggers": {
            "hikari": {"level": "INFO"},
            "lightbulb": {"level": "DEBUG"},
        },
    },
)

client = lightbulb.client_from_app(botapp)