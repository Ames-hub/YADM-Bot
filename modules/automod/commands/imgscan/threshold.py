from modules.automod.commands.imgscan.subgroup import imgscan_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@imgscan_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="threshold",
    description="Change the threshold for how certain the AI is before it flags an image."
):
    
    threshold = lightbulb.integer("threshold", "The threshold as a percentage", min_value=1, max_value=100)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("img-am-threshold", ctx, hikari.Permissions.ADMINISTRATOR)

        embed = (
            hikari.Embed(
                title="Threshold Set",
                description=f"The AI will now only flag images at {self.threshold}% certainty.",
                colour=0x0000ff
            )
        )

        if self.threshold <= 75:
            embed.add_field(
                name="Low Threshold Caution",
                value="Thresholds below 75 percent can result in a great deal of false-positives. Recommended threshold is ~90%"
            )
        elif self.threshold > 95:
            embed.add_field(
                name="High Threshold Caution",
                value="Thresholds above 95 percent can result in many obviously NSFW images not being caught. Recommended threshold is ~90%"
            )

        # Converts threshold from 100 to 1 or 70 to 0.7
        self.threshold = self.threshold / 10
        success = dbguild(ctx.guild_id).set.nsfw_scan_threshold(self.threshold)
        if success:
            await ctx.respond(embed)
            
            # Once we've responded, add a footer and turn it into a log
            embed.set_footer(
                text=f"This was done by {ctx.user.mention}"
            )

            await server_logs(ctx.guild_id).create_entry(embed)
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failure to update",
                    description="There was an error when we tried to update the threshold, please try again later."
                )
            )