from modules.moderation.logging.subgroup import logging_subgroup
from library.database.auditing import logs_config, server_logs
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_set_log_channel(guild_id:int, channel_id:int, user_id:int, responder_func):
    config = logs_config(guild_id)
    logs = server_logs(guild_id)

    # Alert logs if a user is clearing the log channel config so it won't record
    if channel_id == None:
        old_log_channel = config.get_logs_channel()
        if old_log_channel:
            await logs.create_entry(
                hikari.Embed(
                    title="Logging channel removed",
                    description=f"<@{user_id}> Has removed the logging channel",
                    colour=0xff0000
                )
            )

    success = config.set_logs_channel(channel_id)
    if success:
        await responder_func(
            hikari.Embed(
                title="Log Channel Set!",
                description=f"The log channel has been set to <#{channel_id}>",
                color=0x00ff00
            )
        )

        if channel_id is not None:
            await logs.create_entry(
                hikari.Embed(
                    title="Logging channel changed",
                    description=f"<@{user_id}> Has changed the logging channel to here!",
                    colour=0x0000ff
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
        await prechecks("set-logging-channel", ctx, [hikari.Permissions.VIEW_AUDIT_LOG, hikari.Permissions.MANAGE_GUILD])
        return await handle_set_log_channel(
            ctx.guild_id,
            self.channel.id,
            ctx.user.id,
            ctx.respond
        )