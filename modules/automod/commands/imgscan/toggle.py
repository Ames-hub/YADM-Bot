from modules.automod.commands.imgscan.subgroup import imgscan_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@imgscan_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="toggle",
    description="Toggle on or off the image scanner"
):
    
    enabled = lightbulb.boolean("enabled", "Should the Image Scanner scan images?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        success = dbguild(ctx.guild_id).set.do_image_filtering(self.enabled)

        if success:
            embed = (
                hikari.Embed(
                    title="Status Set",
                    description="The AI will now check and flag NSFW images." if self.enabled else "The AI will no longer check for NSFW images."
                )
            )

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
                    description="There was an error when we tried to turn on or off the AI filter, please try again later."
                )
            )