from library.database.guilds import dbguild, violations
from modules.moderation.group import group
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="appeal",
    description="Appeal a violation for a member of the server!"
):
    
    target = lightbulb.user("target", "Who to appeal the violation for")
    violation_id = lightbulb.integer("violation", "The ID of the violation that was incorrect.")
    reason = lightbulb.string("reason", "Why is this violation being appealed?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("appeal", ctx, hikari.Permissions.ADMINISTRATOR)

        appeal_ok = violations.appeal(
            self.violation_id,
            mod_id=ctx.user.id,
            reason=self.reason
        )[0]

        if appeal_ok:
            await ctx.respond(
                hikari.Embed(
                    title="Appealed!",
                    description=f"Violation Case #{self.violation_id} has been appealed, all penalties assosciated undone."
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failed!",
                    description=f"Violation Case #{self.violation_id} could not be appealed."
                )
            )