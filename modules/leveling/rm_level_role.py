from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="rmperk",
    description="Remove a perk that is given to users when they level up"
):

    role = lightbulb.role("role", "What role do you want to no longer give out?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("remove-leveling-perk", ctx, permission=[hikari.Permissions.BAN_MEMBERS, hikari.Permissions.KICK_MEMBERS])  # Admin perms

        guild = dbguild(ctx.guild_id)
        
        # Makes sure it is already a perk
        guild_perk = guild.leveling.get_guild_perk_by_role(self.role.id)
        if guild_perk is None:
            await ctx.respond(
                hikari.Embed(
                    title="Not a perk",
                    description=f"No perk for that role has been added yet.",
                    colour=0xff0000
                )
            )
            return

        success = guild.leveling.rm_level_role(self.role.id)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Removed Successfully",
                    description=f"A user will no longer be given the role {self.role.mention} when leveling up enough.",
                    colour=0x00ff00
                )
            )
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Leveling Perk Removed",
                    description=f"{ctx.user.mention} Has just removed {self.role.mention} as a perk for leveling up.",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="We couldn't remove the role for that level.",
                    colour=0xff0000
                )
            )