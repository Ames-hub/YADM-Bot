from library.database.auditing import logs_config, server_logs
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageDeleteEvent)
async def botfunction(event: hikari.GuildMessageDeleteEvent):
    if event.old_message.member.is_bot or event.old_message.member.is_system:
        return
    if not event.old_message.content:  # might be missing from cache
        return

    logs = logs_config(event.guild_id)
    do_log = logs.msg_deletions.get_do_logging()
    if not do_log:
        return

    embed = (
        hikari.Embed(
            title="Message Deleted",
            description=f"{event.old_message.author.mention} deleted their message in <#{event.channel_id}>.",
            colour=0xff0000
        )
        .add_field(
            name="Old Message",
            value=f"\"{event.old_message.content}\""
        )
    )

    await server_logs(event.guild_id).create_entry(embed)