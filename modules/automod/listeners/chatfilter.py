from library.database.guilds import dbguild
from library import automod
import lightbulb

import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return
    
    if not event.message.content:
        return

    message = event.message.content.strip().lower()
    guilty = automod.check(message, guild_id=event.guild_id)
    if guilty:
        guild = dbguild(event.guild_id)
        embed = hikari.Embed(
            title="Automod Action",
            description=f"{event.author.mention}, your message was {"deleted as it was " if guild.get.do_delete_msg() else ""}found to violate the rules.\n"
        )

        await automod.handle_guilty(event, alert_embed=embed)
        return True
    return True