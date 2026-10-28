from library.database.auditing import logs_config
from library.permissions import prechecks
from modules.logging.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_view_log_channel(guild_id:int):
    log_channel = logs_config(guild_id).get_logs_channel()

    if log_channel:
        embed = hikari.Embed(
            title="Logging Channel",
            description=f"We are sending all of our logs to <#{log_channel}>",
            colour=0x00ff00
        )
    else:
        embed = hikari.Embed(
            title="No Channel",
            description="There's no channel set for us to log to."
        )

    return embed

@group.register
class command(
    lightbulb.SlashCommand,
    name="channel",
    description="Set the logging channel for the bot!"
):
    
    channel = lightbulb.channel("logs_channel", "Where do we send the logs?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("get-logging-channel", ctx, [hikari.Permissions.VIEW_AUDIT_LOG])
        embed = await handle_view_log_channel(ctx.guild_id)
        await ctx.respond(embed)