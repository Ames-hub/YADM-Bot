from library.database.leveling import user_activity, activity_days_threshold
from modules.activity_monitoring.group import group
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="check",
    description="Check if a specific user is considered active in the server!"
):

    target = lightbulb.user("target", "Who do you want us to check?", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-check-active", ctx)

        if not self.target:
            self.target = ctx.user  # if its not someone else, check the calling user.

        ua = user_activity(ctx.guild_id)
        is_active = ua.is_user_active(self.target.id)
        msgs_count = ua.get_msgs_count(self.target.id)

        if is_active:
            activity_text = "**✨ USER IS ACTIVE IN THE COMMUNITY! ✨**"
        else:
            activity_text = "User is not actve in the server."

        await ctx.respond(
            hikari.Embed(
                title=f"User Activity - {ctx.user.display_name}",
                description=(
                    f"{activity_text}\n"
                    f"This user has sent {msgs_count} messages in the last {activity_days_threshold} days!"
                ),
                colour=0xFFD700 if is_active else 0x0000ff
            )
        )