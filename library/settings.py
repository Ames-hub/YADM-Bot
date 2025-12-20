from library.encryption import encryption
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
}

def make_settings_file():
    with open(SETTINGS_PATH, "w") as f:
        json.dump(valid_settings, f, indent=4, separators=(",", ": "))

def _get_value(key, default=None):
    if not os.path.exists(SETTINGS_PATH):
        return default
    with open(SETTINGS_PATH, "r") as f:
        settings:dict = json.load(f)
        return settings.get(key, default)

def _save_value(key, value):
    settings = {}

    if key not in valid_settings.keys():
        raise KeyError("This is a bad key for settings!")

    if key == "allow_registration":
        value = bool(value)
    elif key == "weekday_end":
        ref_dict = {
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
            "sunday": 7,
        }
        value = ref_dict.get(value.lower(), 1)

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
    def bot_token():
        value = _get_value("bot_token", valid_settings["bot_token"])
        if value is not None:
            value = encryption().decrypt(value)
        return value
    
    def prod_mode():
        return _get_value("prod_mode", valid_settings["prod_mode"])
    
    def db_username():
        return _get_value("db_username", valid_settings["db_username"])
    
    def db_password():
        value = _get_value("db_password", valid_settings["db_password"])
        if value is not None:
            value = encryption().decrypt(value)
        return value

    def db_host():
        return _get_value("db_host", valid_settings["db_host"])
    
    def db_port():
        return _get_value("db_port", valid_settings["db_port"])
    
    def db_name():
        return _get_value("db_name", valid_settings["db_name"])
    
    def bot_name():
        return _get_value("bot_name", valid_settings["bot_name"])
    
    def allow_docker_fallback():
        return _get_value("allow_docker_fallback", valid_settings["allow_docker_fallback"])

class set:
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