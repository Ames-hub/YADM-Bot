from library.encryption import encryption
from cachetools import TTLCache
import logging
import json
import os

SETTINGS_PATH = "settings.json"

# Settings that should be encrypted when stored.
encrypted_keys = [
    "bot_token",
    "db_username",
    "db_password",
    "db_host",
    "db_name",
    "nonprod_bot_token",
    "discord_client_secret",
    "session_secret_key",
]

# key: (default value, intended type when set)
valid_settings = {
    "bot_token": (None, str),
    "prod_mode": (False, bool),
    "db_username": (None, str),
    "db_password": (None, str),
    "db_host": (None, str),
    "db_port": (None, int),
    "db_name": (None, str),
    "bot_name": (None, str),
    "primary_maintainer": (None, int),
    "ai_vision_enabled": (True, bool),
    "nonprod_bot_token": (None, str),
    "observation_mode": (False, bool),
    "observed_guilds": ([], list),
    "web_port": (8040, int),
    "discord_client_id": (None, str),
    "discord_client_secret": (None, str),
    "discord_redirect_uri": (None, str),
    "session_secret_key": (None, str),
    # Mainydb is light and small. Good for small deployments where its just the bot running.
    # But, its less ideal for running with the webUI. In fact, its not practically possible.
    # So when this is False, we use Postgres instead.
    "prefer_mainydb": (True, bool),
    "webui-hostname": (None, str),
    "force-use-sqlite": (False, bool),
    "shard_count": (1, int),
}


def _default(key):
    """Return the default value for a settings key."""
    return valid_settings[key][0]


def _intended_type(key):
    """Return the intended type for a settings key."""
    return valid_settings[key][1]


def make_settings_file():
    # Only write the plain default values, not the (default, type) tuples.
    defaults = {key: default for key, (default, _type) in valid_settings.items()}
    with open(SETTINGS_PATH, "w") as f:
        json.dump(defaults, f, indent=4, separators=(",", ": "))


class observe_conf:
    @staticmethod
    def set_enabled(value: bool):
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)

        settings["observation_mode"] = bool(value)

        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)

        return True

    @staticmethod
    def get_enabled():
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)

        try:
            return settings["observation_mode"]
        except KeyError:
            return _default("observation_mode")

    @staticmethod
    def add(guild_id: int):
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)

        if guild_id in settings['observed_guilds']:
            return True

        settings["observed_guilds"].append(guild_id)

        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)

        return True

    @staticmethod
    def remove(guild_id: int):
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


def _get_value(key, default=None, do_cache: bool = True):
    if do_cache and key in cache:
        return cache[key]

    # Load from file
    if not os.path.exists(SETTINGS_PATH):
        result = default
    else:
        with open(SETTINGS_PATH, "r") as f:
            settings: dict = json.load(f)
            result = settings.get(key, default)

    # Decrypt encrypted settings centrally.
    if key in encrypted_keys and result is not None:
        result = encryption().decrypt(result)

    if do_cache:
        cache[key] = result

    return result


def _save_value(key, value):
    settings = {}

    if key not in valid_settings:
        raise KeyError("This is a bad key for settings!")

    # Coerce to the intended type when set (if not None).
    intended_type = _intended_type(key)
    if value is not None:
        # bool is a subclass of int, so watch that.
        if intended_type is bool:
            value = bool(value)
        elif intended_type is int and not isinstance(value, bool):
            value = int(value)
        elif intended_type is list:
            value = list(value)
        elif intended_type is str:
            value = str(value)

    # Encrypt encrypted settings here.
    if key in encrypted_keys and value is not None:
        value = encryption().encrypt(value)

        # Do not use "is" or "if value" here.
        if value == False:
            value = None  # It wasn't encrypted or smth, needs to be reset.

    # Load existing settings if a file exists.
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                logging.warning("Settings file was corrupted. Overwriting.")

    # Avoid logging sensitive values.
    if key in encrypted_keys:
        logging.info(f"Saving bot setting '{key}' with an encrypted value")
    else:
        logging.info(f"Saving bot setting '{key}' with value '{value}'")

    settings[key] = value

    # Write back updated settings.
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)

    # Clear potentially stale cached values.
    cache.pop(key, None)

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


class setgroup:
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
    @staticmethod
    def force_use_sqlite() -> bool:
        return _get_value("force-use-sqlite", _default("force-use-sqlite"), do_cache=True)

    @staticmethod
    def webui_hostname() -> str:
        return _get_value("webui-hostname", _default("webui-hostname"), do_cache=True)

    @staticmethod
    def prefer_mainydb() -> bool:
        return _get_value("prefer_mainydb", _default("prefer_mainydb"), do_cache=True)

    @staticmethod
    def session_secret_key() -> str:
        return _get_value("session_secret_key", _default("session_secret_key"), do_cache=True)

    @staticmethod
    def discord_redirect_uri() -> str:
        return _get_value("discord_redirect_uri", _default("discord_redirect_uri"), do_cache=True)

    @staticmethod
    def discord_client_id() -> str:
        return _get_value("discord_client_id", _default("discord_client_id"), do_cache=True)

    @staticmethod
    def discord_client_secret() -> str:
        return _get_value("discord_client_secret", _default("discord_client_secret"), do_cache=True)

    @staticmethod
    def web_port() -> int:
        return _get_value("web_port", _default("web_port"), do_cache=True)

    @staticmethod
    def appropriate_bot_token() -> str:
        if get.prod_mode():
            return get.bot_token()
        else:
            return get.nonprod_bot_token()

    @staticmethod
    def bot_token() -> str:
        return _get_value("bot_token", _default("bot_token"), do_cache=True)

    @staticmethod
    def prod_mode() -> bool:
        return _get_value("prod_mode", _default("prod_mode"), do_cache=True)

    @staticmethod
    def db_username() -> str:
        return _get_value("db_username", _default("db_username"), do_cache=True)

    @staticmethod
    def db_password() -> str:
        return _get_value("db_password", _default("db_password"), do_cache=True)

    @staticmethod
    def db_host() -> str:
        return _get_value("db_host", _default("db_host"), do_cache=True)

    @staticmethod
    def db_port() -> int:
        return _get_value("db_port", _default("db_port"), do_cache=True)

    @staticmethod
    def db_name() -> str:
        return _get_value("db_name", _default("db_name"), do_cache=True)

    @staticmethod
    def bot_name() -> str:
        return _get_value("bot_name", _default("bot_name"), do_cache=True)

    @staticmethod
    def primary_maintainer() -> int:
        return _get_value("primary_maintainer", _default("primary_maintainer"), do_cache=True)

    @staticmethod
    def ai_vision_enabled() -> bool:
        return _get_value("ai_vision_enabled", _default("ai_vision_enabled"), do_cache=False)

    @staticmethod
    def nonprod_bot_token() -> str:
        return _get_value("nonprod_bot_token", _default("nonprod_bot_token"), do_cache=True)

    @staticmethod
    def shard_count() -> int:
        return _get_value("shard_count", _default("shard_count"), do_cache=True)


class set:
    @staticmethod
    def force_use_sqlite(value: bool):
        return _save_value("force-use-sqlite", value)

    @staticmethod
    def webui_hostname(value: str):
        return _save_value("webui-hostname", value)

    @staticmethod
    def prefer_mainydb(value: bool):
        return _save_value("prefer_mainydb", value)

    @staticmethod
    def session_secret_key(value: str):
        return _save_value("session_secret_key", value)

    @staticmethod
    def discord_client_id(value: int):
        return _save_value("discord_client_id", value)

    @staticmethod
    def discord_client_secret(value: str):
        return _save_value("discord_client_secret", value)

    @staticmethod
    def discord_redirect_uri(value: str):
        return _save_value("discord_redirect_uri", value)

    @staticmethod
    def web_port(value: int):
        return _save_value("web_port", value)

    @staticmethod
    def bot_token(value):
        return _save_value("bot_token", value)

    @staticmethod
    def prod_mode(value: bool):
        return _save_value("prod_mode", bool(value))

    @staticmethod
    def db_username(value: str):
        return _save_value("db_username", value)

    @staticmethod
    def db_password(value: str):
        return _save_value("db_password", value)

    @staticmethod
    def db_host(value: str):
        return _save_value("db_host", value)

    @staticmethod
    def db_port(value: int):
        return _save_value("db_port", int(value))

    @staticmethod
    def db_name(value: str):
        return _save_value("db_name", value)

    @staticmethod
    def bot_name(value: str):
        return _save_value("bot_name", value)

    @staticmethod
    def primary_maintainer(value: int):
        return _save_value("primary_maintainer", int(value))

    @staticmethod
    def ai_vision_enabled(value: bool):
        return _save_value("ai_vision_enabled", bool(value))

    @staticmethod
    def nonprod_bot_token(value: str):
        return _save_value("nonprod_bot_token", value)

    @staticmethod
    def shard_count(value: int):
        return _save_value("shard_count", value)