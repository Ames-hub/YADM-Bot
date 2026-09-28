from library.database.guilds import muting, dbguild
from library.database.auditing import server_logs
from library import datastore as ds
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_task():
    all_mutes = muting.list_all_mutes(active_only=True)

    for mute_case in all_mutes:
        now = datetime.now().timestamp()
        if now >= mute_case.scheduled_unmute:
            guild = dbguild(mute_case.guild_id)
            await guild.muting.unmute_member(mute_case.user_id, do_dm=True)

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False), auto_start=True)
async def unmute_timer_task() -> None:
    await handle_task()