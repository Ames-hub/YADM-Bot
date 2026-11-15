from library.database.leveling import user_activity, guild_leveling
from modules.activity_monitoring.group import group
from library.permissions import prechecks, perms
from library.database import auditing
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="addperk",
    description="Add a perk for users sending a set amount of messages."
):

    perkrole = lightbulb.role("perkrole", "Which role do we give for the amount of messages?")
    msgs_req = lightbulb.integer("msgs_required", "How many messages must they send for the role to be given?", min_value=1)
    operator = lightbulb.string(
        "requirement", "Which maths operator do we apply in handing out this role? (Default >=)",
        choices=[
            lightbulb.Choice("(>) Greater than X Messages", "GT"),
            lightbulb.Choice("(<) Less Than X Messages", "LT"),
            lightbulb.Choice("(>=) Greater than or equal to X Messages", "GTE"),
            lightbulb.Choice("(<=) Less than or Equal to X Messages", "LTE"),
        ],
        default="GTE"
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-add-perk", ctx, [hikari.Permissions.MANAGE_GUILD, hikari.Permissions.MANAGE_ROLES])

        # Checks if the user has permission to do this
        user_perms = perms.get_user_permissions(ctx.guild_id, ctx.user.id)
        if (
                # Checks all the perms of the role are perms the user has, denies if they don't have all.
                (user_perms & self.perkrole.permissions) != self.perkrole.permissions
                and
                # Allows admins to bypass this check
                (user_perms & hikari.Permissions.ADMINISTRATOR) == 0
            ):
            await ctx.respond(
                hikari.Embed(
                    title="Bad Permissions",
                    description="The role you want to give has more permissions than the role you want to give",
                    colour=0xff0000
                )
            )
            return

        ua = user_activity(ctx.guild_id)
        try:
            success = ua.add_role_perk(self.perkrole.id, self.msgs_req, self.operator)
        except user_activity.errors.perk_exists as err:
            await ctx.respond(
                hikari.Embed(
                    title="Perk Already Exists",
                    description=f"This perk already exists as a perk for sending {err.record.msgs_required} messages a week."
                )
            )
            return

        if success:
            leveling = guild_leveling(ctx.guild_id)

            # If leveling is enabled and the role is for a specific user level, integrate the two functions.
            leveling_perk = leveling.get_guild_perk_by_role(self.perkrole.id)
            is_leveling_perk = (
                leveling_perk is not None
                and
                leveling.get_enabled() is True
            )

            embed = hikari.Embed(
                title="Activity Perk Added",
                description=f"If a user sends {self.msgs_req} messages in a week, they'll be given the role <@&{self.perkrole.id}>",
                colour=0x00ff00
            )
            if is_leveling_perk:
                embed.add_field(
                    name="User Leveling",
                    value=(
                        "The selected role is also a perk for leveling up in the server, "
                        "so the new requirements for getting that role is having level "
                        f"{leveling_perk.level_needed} and {self.msgs_req} messages sent!"
                    )
                )
            await ctx.respond(embed)
            await auditing.server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Activity Perk Added",
                    description=(
                        f"<@{ctx.user.id}> Set it so If a user sends {self.msgs_req} "
                        f"messages in a week, they'll be given the role <@&{self.perkrole.id}>"
                    ),
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't add the role perk!",
                    colour=0xff0000
                )
            )
