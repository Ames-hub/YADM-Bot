from library.mainydb import guild_icons
import lightbulb
import logging
import hikari

loader = lightbulb.Loader()

async def handle_task(event: hikari.events.GuildUpdateEvent):
    """
    This is a non-essential cosmetics task for the WebUI.
    It basically looks for when the server icon gets changed, and if it gets changed, it deletes our out-dated cached version of it.
    """
    if event.guild.icon_hash == event.old_guild.icon_hash:
        # Their roles have not changed, so that means its a change not relevant for our purposes.
        return

    deleted = guild_icons.destroy(event.guild_id)
    if not deleted:
        logging.warning(f"Task could not delete guild icon for guild {event.guild_id} for some reason.")
    # We'll re-archive it next time it's needed.

@loader.listener(hikari.events.GuildUpdateEvent)
async def listener(event: hikari.events.GuildUpdateEvent):
    await handle_task(event)