from modules.automod.commands.muting.subgroup import muting_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@muting_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="set_role",
    description="Set which role is to be used for muting users."
):
    
    role = lightbulb.role("mute_role", "Which role is to be assigned for muting")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)
        success = guild.set.muted_role_id(int(self.role.id))

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Set",
                    description=f"The mute role has been set to <@&{self.role.id}>"
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failure",
                    description=f"The mute role was not able to be set!"
                )
            )