from modules.automod.commands.muting.subgroup import muting_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
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
        await prechecks("set-mute-role", ctx, hikari.Permissions.ADMINISTRATOR)

        guild = dbguild(ctx.guild_id)
        success = guild.set.muted_role_id(int(self.role.id))

        if success:
            embed = hikari.Embed(
                title="Muted Role Set",
                description=f"The mute role has been set to <@&{self.role.id}>"
            )
            await ctx.respond(embed)
            server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Muted Role Set",
                    description=f"The mute role has been set to <@&{self.role.id}> by {ctx.user.mention}"
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failure",
                    description=f"The mute role was not able to be set!"
                )
            )