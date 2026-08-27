from library.permissions import perms
from website import memory
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_task(event: hikari.events.MemberUpdateEvent):
    """
    This is an essential permissions task for the WebUI.
    This looks for user role updates, and haves it check if they're still an admin. If they are, it does nothing. If not, it lets the web UI know.
    """
    old_roles = event.old_member.role_ids
    new_roles = event.member.role_ids
    if old_roles == new_roles:
        # Their roles have not changed, so that means its a change not relevant for our purposes.
        return

    user_perms = await perms.get_user_permissions(event.guild_id, event.user_id)
    if hikari.Permissions.ADMINISTRATOR in user_perms:
        return
    else:
        memory.remove_guild_session(guild_id=event.guild_id, discord_user_id=event.user_id)

@loader.listener(hikari.events.MemberUpdateEvent)
async def listener(event: hikari.events.MemberUpdateEvent):
    await handle_task(event)