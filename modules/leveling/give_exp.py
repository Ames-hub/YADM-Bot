from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="give",
    description="Give an amount of EXP to a user."
):

    give_points = lightbulb.integer("points", "How many points should we give?", min_value=1)
    target = lightbulb.user("target", "Who do you want this to affect?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("give-leveling-exp", ctx, permission=[hikari.Permissions.MANAGE_MESSAGES])

        guild = dbguild(ctx.guild_id)

        if not guild.leveling.get_enabled():
            await ctx.respond(
                hikari.Embed(
                    title="Leveling Disabled",
                    description="You cannot give a user chat exp while leveling is disabled.",
                    colour=0xff9c00
                )
            )
            return

        result = guild.leveling.give_exp(self.target.id, msgs=self.give_points, check_level=True)
        success = result['success']
        lvled_up = result['lvl_is_diff']

        if success:
            embed = hikari.Embed(
                title="Points Given",
                description=f"This user has been given {self.give_points} points",
                colour=0x00ff00
            )
            if lvled_up:
                embed.add_field(
                    name="Level Up!",
                    value=f"User levelled up to level {result['new_lvl']}."
                )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Leveling EXP Given",
                    description=f"{ctx.user.mention} Has just given {self.give_points}x points to {self.target.mention}",
                    colour=0x00ff00
                )
            )
        else:
            embed = hikari.Embed(
                title="Failure",
                description="Could not give those points to the user!",
                colour=0xff0000
            )
            await ctx.respond(embed)