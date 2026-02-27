from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import perms
import lightbulb
import hikari
import time

loader = lightbulb.Loader()

async def handle_mute_user(guild_id:int, duration_in_seconds:int, user_id:int, respond_func):
    guild = dbguild(guild_id)

    success = await guild.muting.mute_member(user_id, duration_in_seconds, hardmute=False)

    if success:
        await respond_func(
            hikari.Embed(
                title="Muted!",
                description=f"Member has been muted until: <t:{time.time() + duration_in_seconds}>",
                colour=0x0000ff
            )
        )
    else:
        await respond_func(
            hikari.Embed(
                title="Error!",
                description="Couldn't mute this member for some reason.",
                colour=0xff0000
            )
        )

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
        
        duration_in_seconds = self.duration_minutes * 60
        
        return await handle_mute_user(
            ctx.guild_id,
            duration_in_seconds,
            ctx.user.id,
            ctx.respond
        )