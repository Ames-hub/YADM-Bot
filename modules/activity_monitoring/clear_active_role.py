from modules.activity_monitoring.group import group
from library.database.leveling import user_activity
from library.database.auditing import server_logs
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="clearactiverole",
    description="Disable giving the active-user role to active users"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("activity-clear-active-role", ctx, [hikari.Permissions.MANAGE_ROLES, hikari.Permissions.MANAGE_GUILD])

        ua = user_activity(ctx.guild_id)
        role_id = ua.get_guild_active_role()
        if not role_id:
            await ctx.respond(
                hikari.Embed(
                    title="No Active Role",
                    description="There is no currently existing active role to clear!"
                )
            )
            return

        success = ua.set_guild_active_role(None)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Role Cleared",
                    description=(
                        "The role will not be given to users anymore until you set the active role again with `/activity setactiverole`\n"
                        "Activity perks for talking enough will still apply unless you disable activity monitoring entirely."
                    ),
                    colour=0x00ff00
                )
            )
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Active Member Role Cleared",
                    description=(
                        f"The role <@&{role_id}> will not be given to users anymore until you set the active role again with `/activity setactiverole`\n"
                        "Activity perks for talking enough will still apply unless you disable activity monitoring entirely.\n\n"
                        f"This change was made by {ctx.user.mention}"
                    ),
                    colour=0x0000ff
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Unknown error",
                    description="Couldn't do that!",
                    colour=0xff0000
                )
            )