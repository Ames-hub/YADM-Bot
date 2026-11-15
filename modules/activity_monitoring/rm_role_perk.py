from modules.activity_monitoring.group import group
from library.database.leveling import user_activity
from library.permissions import prechecks
from library.database import auditing
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="rmperk",
    description="Remove a perk for sending a set amount of messages."
):

    role = lightbulb.role("perkrole", "Which role do you want to remove as a perk?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-rm-perk", ctx, [hikari.Permissions.MANAGE_GUILD, hikari.Permissions.MANAGE_ROLES])

        ua = user_activity(ctx.guild_id)
        try:
            success = ua.remove_role_perk(self.role.id)
        except user_activity.errors.perk_not_found:
            await ctx.respond(
                hikari.Embed(
                    title="Does not Exists",
                    description=f"This role does not exist as a perk yet."
                )
            )
            return

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Activity Perk Removed",
                    description=f"Users will no longer be given the role <@&{self.role.id}> if they send many messages.",
                    colour=0x00ff00
                )
            )
            await auditing.server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Activity Perk Removed",
                    description=(
                        f"{ctx.user.mention} Set it so that users will no longer "
                        f"be given the role <@&{self.role.id}> if they send many messages."
                    ),
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't remove the role perk",
                    colour=0xff0000
                )
            )
