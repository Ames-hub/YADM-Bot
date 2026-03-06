from library.database.welcomer import welcomer
from library.database.guilds import dbguild
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_userjoin_event(guild_id, user_display_name, target_channel):
    wc = welcomer(guild_id)
    if not wc.is_enabled():
        return

    embed = (
        hikari.Embed(
            title=f"{user_display_name} Has Joined",
            description=wc.get_welcome_msg(),
            colour=0x00ff00
        )
    )

    try:
        await botapp.rest.create_message(
            channel=target_channel,
            embed=embed
        )
    except (hikari.UnauthorizedError, hikari.ForbiddenError, hikari.NotFoundError):
        pass

@botapp.listen(hikari.events.MemberCreateEvent)
async def listener(event: hikari.events.MemberCreateEvent):
    guild = dbguild(event.guild_id)

    welcomer_channel = guild.welcomer.get_channel()
    if not welcomer_channel:
        welcomer_channel = event.get_guild().system_channel_id
        if not welcomer_channel:
            channel = await botapp.rest.fetch_guild(event.guild_id)
            welcomer_channel = channel.system_channel_id

    await handle_userjoin_event(
        event.guild_id,
        event.user.display_name,
        welcomer_channel
    )