from modules.automod.commands.spam.subgroup import spam_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@spam_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="toggle",
    description="Toggle on or off the spam filter for this server.",
):
    
    enabled = lightbulb.boolean("enabled", "Whether to enable or disable the spam filter.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)
        success = guild.set.do_filter_spam(self.enabled)

        logs = server_logs(ctx.guild_id)
        logs.create_entry(
            hikari.Embed(
                title="Spam Filter Toggled",
                description=f"User {ctx.user.mention} has {'enabled' if self.enabled else 'disabled'} the spam filter.",
                color=0xFFA500,  # Orange color for a warning-type log
            )
        )

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Success",
                    description=f"Spam filter has been {'enabled' if self.enabled else 'disabled'}.",
                    color=0x00FF00,
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error",
                    description="Failed to update the spam filter setting.",
                    color=0xFF0000,
                )
            )