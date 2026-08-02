from library.database.joinroles import joinroles
from modules.roles_on_join.group import group
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_joinroles_get(guild_id:int, respond_func):
    jr = joinroles(guild_id)
    roles_list = jr.get_roles()

    if len(roles_list) == 0:
        await respond_func(
            hikari.Embed(
                title="No Join Roles!",
                description="There are no join roles for this server.",
                color=0xff0000
            )
        )
        return True

    embed = (
        hikari.Embed(
            title="Join Roles",
            description=f"These are the roles that will be given to someone when they join",
            colour=0x00ff00
        )
    )

    roles_txt = ""
    for role in roles_list:
        roles_txt += f"<@&{role}>\n"

    embed.add_field(
        value=roles_txt
    )

    await respond_func(embed)
    return True

@group.register
class command(
    lightbulb.SlashCommand,
    name="list",
    description="List all roles given to new members!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("get joinroles", ctx, permission=hikari.Permissions.MANAGE_ROLES)
        return await handle_joinroles_get(int(ctx.guild_id), ctx.respond)