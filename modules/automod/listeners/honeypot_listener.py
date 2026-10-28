from library.database.guilds import dbguild
from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

WINDOW_SECONDS = 5
MIN_MESSAGES = 4  # Must be at least 2, or the maths breaks.

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    guild = dbguild(event.guild_id)
    if not guild.honeypot.get_enabled():
        return

    honeypot_channel = guild.honeypot.get_channel()
    if not event.channel_id == honeypot_channel:
        return
    else:
        await event.message.delete()
        await guild.honeypot.handle_tripped(event.author.id)