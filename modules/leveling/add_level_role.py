from library.database.guilds import dbguild, server_logs
from modules.leveling.exp_subgroup import exp_subgroup
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@exp_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="addperk",
    description="Add a perk that is given to users when they level up"
):

    level = lightbulb.integer("level", "What level do we give the role at?", min_value=1)
    role = lightbulb.role("role", "What role do we give?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("add-leveling-perk", ctx, permission=[hikari.Permissions.ADMINISTRATOR])

        guild = dbguild(ctx.guild_id)
        success = guild.leveling.add_level_role(self.role.id, self.level)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Added",
                    description=f"When a user reaches level {self.level}, they'll be given the role {self.role.mention}",
                    colour=0x00ff00
                )
            )
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Leveling Perk Added",
                    description=f"{ctx.user.mention} Has just added {self.role.mention} as a perk for leveling up to lvl {self.level}",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="We couldn't add the role for that level.",
                    colour=0xff0000
                )
            )