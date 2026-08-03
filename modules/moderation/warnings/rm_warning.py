from modules.moderation.warnings.subgroup import warnings_subgroup
from library.database.guilds import dbguild
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_rm_warn(guild_id:int, warn_id:int, responder_func):
    guild = dbguild(guild_id)

    success = guild.warnings.revoke_warning(
        warn_id=warn_id
    )
    
    if success:
        await responder_func(
            hikari.Embed(
                title="Warn Revoked",
                description="The logged warning has been forgiven.",
                color=0x00ff00
            )
        )
    else:
        await responder_func(
            hikari.Embed(
                title="Error!",
                description="The logged warning was not able to be forgiven! Please try again.",
                color=0xff0000
            )
        )
    

@warnings_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="revoke",
    description="Revoke a warning from someone's account"
):
    
    warn_id = lightbulb.integer("warn_id", "What warning do you want to revoke?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("rm warning", ctx, hikari.Permissions.ADMINISTRATOR)
        return await handle_rm_warn(
            ctx.guild_id,
            self.warn_id,
            ctx.respond
        )