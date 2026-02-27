from modules.automod.commands.text.subgroup import text_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import perms
from lightbulb import Choice
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="intensity",
    description="Change the level of the text automoderation."
):
    
    level = lightbulb.string("level", "The level of the automod", choices=[Choice("Low", "low"), Choice("Medium", "medium"), Choice("High", "high")])

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        level = self.level.lower()

        if level == "low":
            intensity = 1
        elif level == "medium":
            intensity = 2
        elif level == "high":
            intensity = 3

        guild = dbguild(ctx.guild_id)
        success = guild.set.set_text_filter_level(intensity)

        if success:
            embed = hikari.Embed(
                title="Updated",
                description=f"Your automoderation level has been updated to level {intensity}.",
                color=0x00ff00
            )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).log(
                hikari.Embed(
                    title="Text Filter Intensity",
                    description=f"Your text automoderation level has been updated to level {intensity} by {ctx.user.mention}",
                    color=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failure",
                    description="Couldn't update the automoderation level! Please try again, or file a bug report.",
                    color=0xff0000
                )
            )