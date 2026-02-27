from modules.moderation.logging.subgroup import logging_subgroup
from library.database.auditing import logs_config
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_set_log_channel(guild_id:int, channel_id:int, responder_func):
    config = logs_config(guild_id)
    success = config.set_logs_channel(channel_id)
    if success:
        await responder_func(
            hikari.Embed(
                title="Log Channel Set!",
                description=f"The log channel has been set to <#{channel_id}>",
                color=0x00ff00
            )
        )
        return
    else:
        await responder_func(
            hikari.Embed(
                title="Error!",
                description=f"Couldn't set the logs channel to <#{channel_id}>",
                color=0xff0000
            )
        )
        return

@logging_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="channel",
    description="Set the logging channel for the bot!"
):
    
    channel = lightbulb.channel("logs_channel", "Where do we send the logs?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)
        return await handle_set_log_channel(
            ctx.guild_id,
            self.channel.id,
            ctx.respond
        )