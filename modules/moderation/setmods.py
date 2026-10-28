from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="setmods",
    description="Decide who is the moderator of the server by a role."
):
    
    target_role = lightbulb.user("role", "Which role will all moderators have?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("moderation setmods", ctx, hikari.Permissions.ADMINISTRATOR)
        guild = dbguild(ctx.guild_id)

        success = guild.set.mod_role_id(self.target_role.id)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Moderator Role Set",
                    description="All users with this role will now be treated as moderators (ontop of those will sufficient permissions 😉)",
                    colour=0x0000ff
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Couldn't set role",
                    description="For some reason we couldn't set that role as the mod role!"
                )
            )