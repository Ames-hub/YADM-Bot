from modules.activity_monitoring.group import group
from library.database.leveling import user_activity
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="setactiverole",
    description="Set the role that's given to active users"
):

    role = lightbulb.role("role", "The role that's given to the user's when they're active in the server.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-set-active-role", ctx)

        ua = user_activity(ctx.guild_id)
        success = ua.set_guild_active_role(self.role.id)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Role Set",
                    description="That role will be given to users who send more than 25 messages per week.",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Unknown error",
                    description="Couldn't do that!",
                    colour=0xff0000
                )
            )