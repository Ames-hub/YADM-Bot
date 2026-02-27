from library.database.welcomer import welcomer
from modules.welcomer.group import group
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_toggle_event(enabled:bool, guild_id:int, respond_func):
    wc = welcomer(guild_id)

    success = wc.set_enabled(enabled)
    if not success:
        await respond_func(
            hikari.Embed(
                title="Failed!",
                description="Couldn't toggle on or off the welcomer? This is a bug!",
                colour=0xff0000
            )
        )
        return

    embed = (
        hikari.Embed(
            title="Welcomer Module",
            description="Welcomer has been disabled!" if not enabled else f"{get.bot_name()} will now welcome those who join!",
            colour=0x00ff00
        )
    )

    await respond_func(embed)

@group.register
class command(
    lightbulb.SlashCommand,
    name="enabled",
    description="Set whether the welcomer is enabled!"
):

    enabled = lightbulb.boolean("enabled", "Do we welcome people?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        return await handle_toggle_event(self.enabled, ctx.guild_id, ctx.respond)