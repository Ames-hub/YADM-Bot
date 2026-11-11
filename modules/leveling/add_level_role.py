from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
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

        # Checks if its already a perk
        guild_perk = guild.leveling.get_guild_perk_by_role(self.role.id)
        if guild_perk is not None:
            await ctx.respond(
                hikari.Embed(
                    title="Already a perk",
                    description=f"Cannot add that perk, because this role is already a perk for level {guild_perk.level_needed}.",
                    colour=0xff0000
                )
            )
            return

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