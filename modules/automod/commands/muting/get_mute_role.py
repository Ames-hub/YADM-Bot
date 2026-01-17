from modules.automod.commands.muting.subgroup import muting_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@muting_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="get_role",
    description="Get which role is to be used for muting users."
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)
        role_id = guild.get.muted_role_id()

        if role_id:
            await ctx.respond(
                hikari.Embed(
                    title="Found",
                    description=f"The mute role is <@&{role_id}>"
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="No Mute Role.",
                    description="This server doesn't have a configured mute role.\n"
                    "(Don't worry, if we need one, we'll make one)"
                )
            )