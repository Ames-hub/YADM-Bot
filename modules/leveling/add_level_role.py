from library.database.guilds import dbguild, server_logs
from library.database.leveling import user_activity
from library.permissions import prechecks
from modules.leveling.group import group
from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="addperk",
    description="Add a perk that is given to users when they level up"
):

    target_level = lightbulb.integer("level", "What level do we give the role at?", min_value=1)
    perk_role = lightbulb.role("role", "What role do we give?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("add-leveling-perk", ctx, permission=[hikari.Permissions.ADMINISTRATOR])

        guild = dbguild(ctx.guild_id)
        ua = user_activity(ctx.guild_id)

        # Checks if its already a perk
        guild_perk = guild.leveling.get_guild_perk_by_role(self.perk_role.id)
        if guild_perk is not None:
            await ctx.respond(
                hikari.Embed(
                    title="Already a perk",
                    description=f"Cannot add that perk, because this role is already a perk for level {guild_perk.level_needed}.",
                    colour=0xff0000
                )
            )
            return
        
        activity_role = ua.get_guild_active_role()
        if activity_role == self.perk_role.id:
            await ctx.respond(
                hikari.Embed(
                    title="Role Taken",
                    description="This role is already being used as a reward for community-active users, please pick another role.",
                    colour=0xff0000
                )
            )
            return

        success = guild.leveling.add_level_role(self.perk_role.id, self.target_level)

        if success:

            embed = hikari.Embed(
                title="Added",
                description=f"When a user reaches level {self.target_level}, they'll be given the role {self.perk_role.mention}",
                colour=0x00ff00
            )

            activity_perk = ua.get_role_perk(self.perk_role.id)
            is_activity_perk = (
                activity_perk is not None
                and
                ua.get_guild_enabled() is True
            )
            if is_activity_perk:
                operator = ds.d["activity_operator_map"].get(activity_perk.operator, ">=")
                embed.add_field(
                    name="User Activity",
                    value=(
                        f"The selected role is also a perk for sending {operator}{activity_perk.msgs_required} messages in the server, "
                        f"so the new requirements for getting that role is having {operator}{activity_perk.msgs_required}"
                        f"messages sent over 7 days and having level {self.target_level}!"
                    )
                )

            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Leveling Perk Added",
                    description=f"{ctx.user.mention} Has just added {self.perk_role.mention} as a perk for leveling up to lvl {self.target_level}",
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