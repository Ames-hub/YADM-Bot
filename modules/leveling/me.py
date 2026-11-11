from library.database.guilds import dbguild
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="me",
    description="Get your levelling details!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("leveling-get-me", ctx)

        guild = dbguild(ctx.guild_id)
        user = guild.leveling.get_user(ctx.user.id)
        board_position = guild.leveling.get_leaderboard_position(ctx.user.id)

        embed = (
            hikari.Embed(
                title=f"{ctx.user.display_name} - Leaderboard",
                description=(
                    f"{user.exp} points • Level {user.level} • Position #{board_position}\n\n"
                ),
                colour=0xffd700
            )
        )

        await ctx.respond(embed)