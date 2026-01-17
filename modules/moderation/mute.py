from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import perms
import lightbulb
import hikari
import time

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="mute",
    description="Mute a member of the server!"
):
    
    user = lightbulb.user("target", "Who to mute")
    duration_minutes = lightbulb.integer("minutes", "How long do we mute them for in minutes?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_MESSAGES, ctx)

        guild = dbguild(ctx.guild_id)
        duration_in_seconds = self.duration_minutes * 60

        success = await guild.muting.mute_member(self.user.id, duration_in_seconds, hardmute=False)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Muted!",
                    description=f"Member has been muted until: <t:{time.time() + duration_in_seconds}>"
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't mute this member for some reason."
                )
            )