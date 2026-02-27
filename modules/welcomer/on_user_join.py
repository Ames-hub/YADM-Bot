from library.database.welcomer import welcomer
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_userjoin_event(guild_id, user_display_name, system_channel_id):
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
            channel=system_channel_id,
            embed=embed
        )
    except (hikari.UnauthorizedError, hikari.ForbiddenError, hikari.NotFoundError):
        pass

@botapp.listen(hikari.events.MemberCreateEvent)
async def listener(event: hikari.events.MemberCreateEvent):
    channel = event.get_guild().system_channel_id
    if not channel:
        channel = await botapp.rest.fetch_guild(event.guild_id)
        channel = channel.system_channel_id

    await handle_userjoin_event(
        event.guild_id,
        event.user.display_name,
        channel
    )