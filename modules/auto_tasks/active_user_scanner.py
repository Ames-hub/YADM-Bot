from library.database.leveling import user_activity
from library.botapp import botapp
import lightbulb

loader = lightbulb.Loader()

@loader.task(lightbulb.uniformtrigger(hours=2, wait_first=False), auto_start=True)
async def scan_users_active() -> None:
    result = user_activity.determine_active()
    newly_active = result['newly_active']
    no_longer_active = result['no_longer_active']

    for guild_id, user_id in newly_active:
        ua = user_activity()
        do_activity_monitoring = ua.get_guild_enabled()
        if do_activity_monitoring:
            role_id = ua.get_guild_active_role()
            await botapp.rest.add_role_to_member(
                guild=guild_id,
                user=user_id,
                role=role_id,
                reason="User was flagged as being active in the community."
            )

    for guild_id, user_id in no_longer_active:
        ua = user_activity()
        do_activity_monitoring = ua.get_guild_enabled()
        if do_activity_monitoring:
            role_id = ua.get_guild_active_role()
            await botapp.rest.remove_role_from_member(
                guild=guild_id,
                user=user_id,
                role=role_id,
                reason="User was flagged as no longer being active in the community."
            )