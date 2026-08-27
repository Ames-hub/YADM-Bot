from library.encryption import encryption
from cachetools import TTLCache
import logging
import json
import os

# Super simple settings system.
SETTINGS_PATH = "settings.json"

valid_settings = {
    "bot_token": None,
    "prod_mode": False,
    "db_username": None,
    "db_password": None,
    "db_host": None,
    "db_port": None,
    "db_name": None,
    "bot_name": None,
    "allow_docker_fallback": True,
    "primary_maintainer": None,
    "ai_vision_enabled": True,
    "nonprod_bot_token": None,  # The token to use while the bot is not in "production" mode
    "observation_mode": False,
    "observed_guilds": [],
    "web_port": 8040,
    "discord_client_id": None,
    "discord_client_secret": None,
    "discord_redirect_uri": None,
    "session_secret_key": None,
    # Mainydb is light and small. Good for small deployments where its just the bot running.
    # But, its less ideal for running with the webUI. In fact, its not practically possible.
    # So when this is False, we use Postgres instead.
    "prefer_mainydb": True
}

def make_settings_file():
    with open(SETTINGS_PATH, "w") as f:
        json.dump(valid_settings, f, indent=4, separators=(",", ": "))

class observe_conf:
    @staticmethod
    def set_enabled(value:bool):
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
        settings["observation_mode"] = bool(value)  # Enforce bool
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return True

    @staticmethod
    def get_enabled():
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
        return settings["observation_mode"]

    @staticmethod
    def add(guild_id:int):
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
        # Don't let it double-up
        if guild_id in settings['observed_guilds']:
            return True
        settings["observed_guilds"].append(guild_id)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return True

    @staticmethod
    def remove(guild_id:int):
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
        settings["observed_guilds"].remove(guild_id)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return True

    @staticmethod
    def get_list():
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
        return settings["observed_guilds"]

cache = TTLCache(maxsize=100, ttl=300)

def _get_value(key, default=None, do_cache: bool=True):
    if do_cache and key in cache:
        return cache[key]

    # Load from file
    if not os.path.exists(SETTINGS_PATH):
        result = default
    else:
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
            result = settings.get(key, default)

    if do_cache:
        cache[key] = result

    return result

def _save_value(key, value):
    settings = {}

    if key not in valid_settings.keys():
        raise KeyError("This is a bad key for settings!")

    # Load existing settings if a file exists
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                logging.warning("Settings file was corrupted. Overwriting.")

    logging.info(f"Saving bot setting '{key}' with value '{value}'")
    settings[key] = value

    # Write back updated settings
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)

    return True

class getgroup:
    def db_details():
        """
        Returns all database connection details as a dictionary.
        """
        return {
            "user": get.db_username(),
            "password": get.db_password(),
            "host": get.db_host(),
            "port": get.db_port(),
            "dbname": get.db_name(),
        }

class setgroup():
    def db_details(details: dict):
        """
        Sets all database connection details from a dictionary.
        Expected keys: dbname, user, password, host, port
        """
        set.db_name(details.get("dbname"))
        set.db_username(details.get("user"))
        set.db_password(details.get("password"))
        set.db_host(details.get("host"))
        set.db_port(details.get("port"))
        return True

class get:
    def prefer_mainydb():
        return _get_value("prefer_mainydb", valid_settings["prefer_mainydb"], do_cache=True)

    def session_secret_key():
        return _get_value("session_secret_key", valid_settings["session_secret_key"], do_cache=True)

    def discord_redirect_uri():
        return _get_value("discord_redirect_uri", valid_settings["discord_redirect_uri"], do_cache=True)

    def discord_client_id():
        return _get_value("discord_client_id", valid_settings["discord_client_id"], do_cache=True)

    def discord_client_secret():
        return _get_value("discord_client_secret", valid_settings["discord_client_secret"], do_cache=True)

    def web_port():
        return _get_value("web_port", valid_settings["web_port"], do_cache=True)

    def appropriate_bot_token():
        if get.prod_mode():
            return get.bot_token()
        else:
            return get.nonprod_bot_token()

    def bot_token():
        value = _get_value("bot_token", valid_settings["bot_token"], do_cache=True)
        if value is not None:
            value = encryption().decrypt(value)
        return value
    
    def prod_mode():
        return _get_value("prod_mode", valid_settings["prod_mode"], do_cache=True)
    
    def db_username():
        return _get_value("db_username", valid_settings["db_username"], do_cache=True)
    
    def db_password():
        value = _get_value("db_password", valid_settings["db_password"], do_cache=True)
        if value is not None:
            value = encryption().decrypt(value)
        return value

    def db_host():
        return _get_value("db_host", valid_settings["db_host"], do_cache=True)
    
    def db_port():
        return _get_value("db_port", valid_settings["db_port"], do_cache=True)
    
    def db_name():
        return _get_value("db_name", valid_settings["db_name"], do_cache=True)
    
    def bot_name():
        return _get_value("bot_name", valid_settings["bot_name"], do_cache=True)
    
    def allow_docker_fallback():
        return _get_value("allow_docker_fallback", valid_settings["allow_docker_fallback"], do_cache=True)

    def primary_maintainer():
        return _get_value("primary_maintainer", valid_settings["primary_maintainer"], do_cache=True)

    def ai_vision_enabled():
        return _get_value("ai_vision_enabled", valid_settings["ai_vision_enabled"], do_cache=False)

    def nonprod_bot_token():
        value = _get_value("nonprod_bot_token", valid_settings["nonprod_bot_token"], do_cache=True)
        if value is not None:
            value = encryption().decrypt(value)
        return value

class set:
    def prefer_mainydb(value:bool):
        return _save_value("prefer_mainydb", value)

    def session_secret_key(value:str):
        return _save_value("session_secret_key", value)

    def discord_client_id(value:int):
        return _save_value("discord_client_id", value)

    def discord_client_secret(value:str):
        return _save_value("discord_client_secret", value)

    def discord_redirect_uri(value:str):
        return _save_value("discord_redirect_uri", value)

    def web_port(value:int):
        return _save_value("web_port", value)

    def bot_token(value):
        # Protect the bot token by encrypting it before saving.
        value = encryption().encrypt(value)
        return _save_value("bot_token", value)

    def prod_mode(value: bool):
        return _save_value("prod_mode", bool(value))
    
    def db_username(value: str):
        return _save_value("db_username", value)
    
    def db_password(value: str):
        value = encryption().encrypt(value)
        return _save_value("db_password", value)
    
    def db_host(value: str):
        return _save_value("db_host", value)
    
    def db_port(value: int):
        return _save_value("db_port", int(value))
    
    def db_name(value: str):
        return _save_value("db_name", value)
    
    def bot_name(value: str):
        return _save_value("bot_name", value)
    
    def allow_docker_fallback(value: bool):
        return _save_value("allow_docker_fallback", bool(value))
    
    def primary_maintainer(value: int):
        return _save_value("primary_maintainer", int(value))
    
    def ai_vision_enabled(value: bool):
        return _save_value("ai_vision_enabled", bool(value))
    
    def nonprod_bot_token(value):
        value = encryption().encrypt(value)
        return _save_value("nonprod_bot_token", str(value))