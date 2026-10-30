from library.database.guilds import dbguild, server_logs
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildChannelDeleteEvent)
async def botfunction(event: hikari.GuildChannelDeleteEvent):
    guild = dbguild(event.guild_id)
    # If the honeypot channel is deleted, delete it in the DB and disable the honeypot.
    if event.channel_id == guild.honeypot.get_channel():
        guild.honeypot.set_channel(None)
        guild.honeypot.set_enabled(False)
        await server_logs(event.guild_id).create_entry(
            hikari.Embed(
                title="Honeypot deleted",
                description=f"The 'honey' channel has been deleted, removing some of your raid protection with the spam-bot honeypot trap.",
                colour=0xffff00
            )
            .set_footer("Run /automod honeypot setup to fix this!")
        )