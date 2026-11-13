from library.database.leveling import user_activity
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.MessageCreateEvent)
async def botfunction(event: hikari.MessageCreateEvent):
    if not event.author.id == get.primary_maintainer():
        return

    if event.message.content == "--scan-active-now":
        await event.message.respond(
            hikari.Embed(
                title="DEBUG COMMAND DETECTED",
                description=(
                    "Primary maintainer has requested all guilds and all users be scanned for weekly activity, "
                    "and that roles be applied accordingly. The changes may take a while to take effect."
                ),
                colour=0x0000ff
            )
        )
        await user_activity.scan_users_active()