from modules.automod.commands.honeypot.subgroup import honeypot_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@honeypot_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="toggle",
    description="Turn off or on the honeypot (disable/enable)"
):
    
    enabled = lightbulb.boolean("enabled", "Should the honey-pot be in operation?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("honeypot toggle", ctx, hikari.Permissions.ADMINISTRATOR)

        guild = dbguild(ctx.guild_id)
        success = guild.honeypot.set_enabled(self.enabled)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Honeypot Toggled",
                    description=(
                        "Honeypot is now looking for people to flag."
                        if self.enabled else
                        "Honeypot will no longer handle bots when they're flagged"
                    )
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failed",
                    description="For some reason, we could not toggle the honeypot.",
                    colour=0xff0000
                )
            )