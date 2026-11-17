from library.settings import get, SETTINGS_PATH, _get_value, valid_settings, encrypted_keys
from library.database.leveling import user_activity
import lightbulb
import hikari
import json

loader = lightbulb.Loader()

@loader.listener(hikari.MessageCreateEvent)
async def botfunction(event: hikari.MessageCreateEvent):
    if not event.author.id == get.primary_maintainer():
        return

    if event.message.content == "--list-settings":
        settings_text = "Listing all bot settings...\n\n"

        with open(SETTINGS_PATH, "r") as f:
            json_file: dict = json.load(f)
            for key, value in json_file.items():
                value = _get_value(key, default=valid_settings[key])  # This handles decryption
                if key in encrypted_keys and value is not None:
                    value = f"||...{value[len(value) // 2::]}||"  # Hides half the key
                
                settings_text += f"**{key}** - {value}, ({type(value).__name__})\n"

        await event.message.respond(
            hikari.Embed(
                title="DEBUG COMMAND DETECTED",
                description=settings_text,
                colour=0x0000ff
            )
        )
        await user_activity.scan_users_active()