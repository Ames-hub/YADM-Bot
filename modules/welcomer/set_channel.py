from library.database.auditing import server_logs
from library.database.welcomer import welcomer
from library.permissions import prechecks
from modules.welcomer.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_toggle_event(channel:int, guild_id:int, respond_func):
    wc = welcomer(guild_id)

    success = wc.set_channel(channel)
    if not success:
        await respond_func(
            hikari.Embed(
                title="Failed!",
                description="Couldn't set the welcomer's channel? This is a bug!",
                colour=0xff0000
            )
        )
        return

    embed = (
        hikari.Embed(
            title="Welcomer Module",
            description=f"The channel has been set to <#{channel}>",
            colour=0x00ff00
        )
    )
    await server_logs(guild_id).create_entry(
        hikari.Embed(
            title="Welcomer Channel",
            description=f"Welcomer channel has been set to <#{channel}>",
            colour=0x00ff00
        )
    )

    await respond_func(embed)

@group.register
class command(
    lightbulb.SlashCommand,
    name="channel",
    description="Set the channel we welcome people in!"
):

    channel = lightbulb.channel("channel", "Which channel do we welcome in?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("welcomer set-channel", ctx, hikari.Permissions.MANAGE_MESSAGES)
        return await handle_toggle_event(self.channel.id, ctx.guild_id, ctx.respond)