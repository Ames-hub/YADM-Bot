from modules.activity_monitoring.group import group
from library.database.leveling import user_activity
from library.permissions import prechecks
from library.database import auditing
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="toggle",
    description="Toggle if we give the role that's given to active users"
):

    enabled = lightbulb.boolean("enabled", "Do we give the active role to active users?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-set-enabled", ctx)

        ua = user_activity(ctx.guild_id)
        success = ua.set_guild_enabled(self.enabled)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Activity Monitoring Enabled",
                    description="When a user starts being active in the server, we'll give them the active role.",
                    colour=0x00ff00
                )
            )
            await auditing.server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Activity Monitoring Enabled",
                    description=f"{ctx.user.mention} enabled activity monitoring for this server.",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't set the enabled status!",
                    colour=0xff0000
                )
            )
