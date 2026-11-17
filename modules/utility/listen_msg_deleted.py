from library.database import observations as obs
from library.database.guilds import dbguild
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageDeleteEvent)
async def botfunction(event: hikari.GuildMessageDeleteEvent):
    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    entry = obs.get_entry(int(event.message_id))
    if entry is None:
        return

    obs.mark_deleted(msg_id=event.message_id, value=True)

@loader.listener(hikari.GuildBulkMessageDeleteEvent)
async def botfunction(event: hikari.GuildBulkMessageDeleteEvent):
    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    for msg_id in event.message_ids:
        entry = obs.get_entry(int(msg_id))
        if not entry:
            continue

        obs.mark_deleted(msg_id=event.message_id, value=True)