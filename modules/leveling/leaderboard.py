from library.database.guilds import dbguild
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="leaderboard",
    description="Get the top 10 chatters of the server!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("levelling-leaderboard", ctx)

        guild = dbguild(ctx.guild_id)
        leaderboard = guild.leveling.get_leaderboard()

        string_list = []
        for user in leaderboard:
            position = guild.leveling.get_leaderboard_position(user.user_id)
            if user.exp != 0:
                if position == 1:
                    string_list.append(f"⭐ #{position} <@{user.user_id}> - Level {user.level}")
                elif position == 2:
                    string_list.append(f"🔷 #{position} <@{user.user_id}> - Level {user.level}")
                elif position == 3:
                    string_list.append(f"🔶 #{position} <@{user.user_id}> - Level {user.level}")
                else:
                    string_list.append(f"#{position} <@{user.user_id}> - Level {user.level}")
            else:
                string_list.append(f"#{position} <@{user.user_id}> - Level 0")

        embed = (
            hikari.Embed(
                title="⭐ Chat Leaderboard ⭐",
                description="The top 10 Chatters of the server are displayed here!"
            )
            .add_field(
                name="Top 10",
                value="\n".join(string_list)
            )
        )

        await ctx.respond(embed)