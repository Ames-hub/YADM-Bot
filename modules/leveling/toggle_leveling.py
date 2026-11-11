from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="toggle",
    description="Set whether or not we track leveling"
):

    enabled = lightbulb.boolean("enabled", "Do we enable leveling or not?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("leveling-set-enabled", ctx, permission=[hikari.Permissions.MANAGE_GUILD, hikari.Permissions.MANAGE_MESSAGES])

        guild = dbguild(ctx.guild_id)
        success = guild.leveling.set_enabled(self.enabled)

        if success:
            stat_text = 'enabled' if self.enabled else 'disabled'
            if self.enabled:
                await ctx.respond(
                    hikari.Embed(
                        title="Leveling enabled",
                        description="We'll start tracking user's EXP for sending messages!",
                        colour=0x0000ff
                    )
                )
            else:
                await ctx.respond(
                    hikari.Embed(
                        title="Leveling Toggled Off",
                        description="User exp will no longer be tracked.",
                        colour=0x0000ff
                    )
                )
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title=f"Leveling {stat_text}",
                    description=f"{ctx.user.mention} Just {stat_text} the user leveling module for the bot.",
                    colour=0xff0000 if not self.enabled else 0x0000ff
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failed to set",
                    description="Couldn't set leveling to that state for some reason.",
                    colour=0xff0000
                )
            )