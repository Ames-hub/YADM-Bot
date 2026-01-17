from modules.moderation.warnings.subgroup import warnings_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
from library import datastore as ds
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

@warnings_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="revoke",
    description="Revoke a warning from someone's account"
):
    
    warn_id = lightbulb.integer("warn_id", "What warning do you want to revoke?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)

        success = guild.warnings.revoke_warning(
            warn_id=self.warn_id
        )
        
        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Warn Revoked",
                    description="The logged warning has been forgiven.",
                    color=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="The logged warning was not able to be forgiven! Please try again.",
                    color=0xff0000
                )
            )
        