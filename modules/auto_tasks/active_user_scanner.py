from library.database.leveling import user_activity
import lightbulb

loader = lightbulb.Loader()

@loader.task(lightbulb.uniformtrigger(hours=2, wait_first=False), auto_start=True)
async def active_scan_task() -> None:
    await user_activity.scan_users_active()