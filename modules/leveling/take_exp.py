from library.database.guilds import dbguild, server_logs
from modules.leveling.exp_subgroup import exp_subgroup
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@exp_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="take",
    description="Remove an amount of EXP from a user."
):

    take_points = lightbulb.integer("points", "How many points should we take?", min_value=1)
    target = lightbulb.user("target", "Who do you want this to affect?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("take-leveling-exp", ctx, permission=[hikari.Permissions.MANAGE_MESSAGES])

        guild = dbguild(ctx.guild_id)
        success = guild.leveling.remove_exp(self.target.id, msgs=self.take_points)

        if success:
            new_user_level = guild.leveling.estimate_level()
            embed = hikari.Embed(
                title="Points Taken",
                description=f"This user has had {self.give_points} points deducted, taking them to level {new_user_level}"
            )
        else:
            embed = hikari.Embed(
                title="Failure",
                description="Could not remove those points from the user!"
            )

        await ctx.respond(embed)

        await server_logs(ctx.guild_id).create_entry(
            hikari.Embed(
                title="Leveling EXP Removed",
                description=f"{ctx.user.mention} Has just taken {self.take_points}x points from {self.target.mention}",
                colour=0xff0000
            )
        )