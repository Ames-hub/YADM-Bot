from modules.moderation.warnings.subgroup import warnings_group
from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()   

@warnings_group.register
class command(
    lightbulb.SlashCommand,
    name="revoke",
    description="Revoke a warning from someone's account"
):
    
    warn_id = lightbulb.integer("warn_id", "What warning do you want to revoke?")
    reason = lightbulb.string("reason", "Why is it being revoked? Was it incorrectly issued?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("rm warning", ctx, hikari.Permissions.MANAGE_MESSAGES)
        guild = dbguild(ctx.guild_id)

        warning = guild.warnings.get_by_id(self.warn_id)
        if not warning:
            await ctx.respond(
                hikari.Embed(
                    title="Warning not found!",
                    description="That warning does not exist, did you enter the ID right?",
                    color=0xff0000
                )
            )
            return

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
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Warn Revoked",
                    description=f"A Warning issued to <@{warning.user_id}> was revoked by <@{warning.moderator_id}>"
                )
                .add_field(
                    name="Reason",
                    value=f"\"{self.reason}\""
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