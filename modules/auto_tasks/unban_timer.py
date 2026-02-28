from library.database.guilds import list_all_bans, dbguild
from library.database.auditing import server_logs
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_task():
    all_bans = list_all_bans()

    for ban in all_bans:
        # If the ban has expired,
        if ban.time_to_unban.timestamp() <= datetime.now().timestamp():
            guild = dbguild(ban.guild_id)
            reason = f"Ban countdown as set by user with ID {ban.moderator_id} had expired"
            try:
                success = await guild.bans.unban_user(
                    user_id=ban.banned_id,
                    reason=reason
                )
                if not success:
                    server_logs(ban.guild_id).create_entry(
                        hikari.Embed(
                            title="Unban Failed",
                            description=f"While attempting to unban <@{ban.banned_id}>, we encountered an error. Please manually unban them."
                        )
                    )
            except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                continue

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def task() -> None:
    await handle_task()