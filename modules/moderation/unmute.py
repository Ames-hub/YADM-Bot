from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import prechecks
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
    
    target = lightbulb.user("target", "Who to mute")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("unmute", ctx, hikari.Permissions.MANAGE_MESSAGES)

        guild = dbguild(ctx.guild_id)

        success = await guild.muting.unmute_member(
            user_id=self.target.id,
            do_dm=True
        )

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Unmuted!",
                    description="Member has been unmuted.",
                    colour=0x0000ff
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't unmute this member for some reason.",
                    colour=0xff0000
                )
            )