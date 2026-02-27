from library.database.joinroles import joinroles
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_roleset_on_join(guild_id, user_id):
    jr = joinroles(guild_id)
    return await jr.add_roles_to_member(user_id)

@botapp.listen(hikari.events.MemberCreateEvent)
async def listener(event: hikari.events.MemberCreateEvent):
    channel = event.get_guild().system_channel_id
    if not channel:
        channel = await botapp.rest.fetch_guild(event.guild_id)
        channel = channel.system_channel_id

    return await handle_roleset_on_join(
        event.guild_id,
        event.user.id
    )