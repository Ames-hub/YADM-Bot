from modules.activity_monitoring.group import group
from library.database.leveling import user_activity
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="threshold",
    description="Set how many messages need to be sent in 1 week for user to be considered active."
):

    amount = lightbulb.integer("amount", "How many messages in 1 week?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-set-threshold", ctx)

        await ctx.respond(
            hikari.Embed(
                title="W.I.P.",
                description="This feature is a work in progress.",
                colour=0xff0000
            )
        )