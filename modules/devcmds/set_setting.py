from library.settings import _save_value, _get_value, get, valid_settings, _intended_type, encrypted_keys
from library.database.leveling import user_activity
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.MessageCreateEvent)
async def botfunction(event: hikari.MessageCreateEvent):
    if not event.author.id == get.primary_maintainer():
        return

    if event.message.content.startswith("--set-setting"):
        text = event.message.content.replace("--set-setting ", "").split(" ")
        if not len(text) == 2:
            await event.message.respond(
                hikari.Embed(
                    title="DEBUG COMMAND ERROR",
                    description="You are missing a key or a value for this setting.",
                    colour=0xff0000
                )
            )
            return
        
        key = text[0]
        new_value = text[1]
        # Determines the type of the value. Always starts as string.
        if new_value.lower() in ["none", "null"]:
            new_value = None
        elif new_value.lower() in ["true", "false", "0", "1"]:
            new_value = bool(new_value)
        elif new_value.isdigit():
            new_value = int(new_value)
        elif new_value.isalnum():
            new_value = str(new_value)  # This is what it already was, just explicitly setting it. 

        # Checks the key is a valid key
        if not key in valid_settings.keys():
            await event.message.respond(
                hikari.Embed(
                    title="DEBUG COMMAND ERROR",
                    description="That key does not exist in the settings.",
                    colour=0xff0000
                )
            )
            return

        # Checks the value is the correct type for the key
        if not type(new_value) == _intended_type(key) and not new_value is None:  # allow all values to be set as None
            await event.message.respond(
                hikari.Embed(
                    title="DEBUG COMMAND ERROR",
                    description=(
                        f"The type of the value you entered ({type(new_value).__name__}) "
                        f"is not valid for the {type(valid_settings[key]).__name__} key you entered."
                    ),
                    colour=0xff0000
                )
            )
            return

        old_value = _get_value(key, default=valid_settings[key])
        _save_value(key, new_value)

        if key in encrypted_keys:
            await event.message.delete()
            await event.author.send(
                hikari.Embed(
                    title="DEBUG COMMAND DETECTED",
                    description=f"Setting \"{key}\" Has been changed from {old_value} to \"{new_value}\" ({type(new_value).__name__})",
                    colour=0x0000ff
                )
            )
        else:
            await event.message.respond(
                hikari.Embed(
                    title="DEBUG COMMAND DETECTED",
                    description=f"Setting \"{key}\" Has been changed from {old_value} to \"{new_value}\" ({type(new_value).__name__})",
                    colour=0x0000ff
                )
            )

        await user_activity.scan_users_active()