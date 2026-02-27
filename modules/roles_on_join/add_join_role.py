from library.database.joinroles import joinroles
from modules.roles_on_join.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_joinrole_add(role_id:int, guild_id:int, respond_func):
    jr = joinroles(guild_id)

    success = jr.add_role(role_id)
    if not success:
        await respond_func(
            hikari.Embed(
                title="Failed!",
                description="Couldn't add the role to the join roles list? This is a bug!",
                colour=0xff0000
            )
        )
        return

    embed = (
        hikari.Embed(
            title="Join Roles",
            description=f"<@&{role_id}> Will be given to new members when they join.",
            colour=0x00ff00
        )
    )

    await respond_func(embed)

@group.register
class command(
    lightbulb.SlashCommand,
    name="add",
    description="Add a role to give new members!"
):

    role = lightbulb.role("role", "What role should members have on join?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        return await handle_joinrole_add(int(self.role.id), int(ctx.guild_id), ctx.respond)