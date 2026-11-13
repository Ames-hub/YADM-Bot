from library.database.auditing import logs_config, server_logs
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageDeleteEvent)
async def botfunction(event: hikari.GuildMessageDeleteEvent):
    deletion_time = datetime.now()  # Save it immediately
    if not event.old_message:
        return
    
    if event.old_message.member.is_bot or event.old_message.member.is_system:
        return
    if not event.old_message.content:  # might be missing from cache
        return

    logs = logs_config(event.guild_id)
    do_log = logs.msg_deletions.get_do_logging()
    if not do_log:
        return

    try:
        audit_logs = await botapp.rest.fetch_audit_log(
            guild=event.guild_id,
            event_type=hikari.AuditLogEventType.MESSAGE_DELETE
        )
    except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
        pass

    mod_id = None
    for auditlog in audit_logs:
        # This should catch who deleted the message 90% of the time.
        # The only edge-case I can imagine is if two mods are deleting the user's messages at the same time.
        # I can't think of any protection against this.
        for snowflake, record in auditlog.entries.items():
            if not record.guild_id == event.guild_id:  # Verifies it happened in the guild
                continue
            if not record.target_id == event.old_message.author.id:  # Verifies the message belongs to the user
                continue
            if not int(record.created_at.timestamp() - deletion_time.timestamp()) <= 10:  # Ensures the message is only recently deleted
                continue
            if not record.options.channel_id == event.channel_id:
                continue

            mod_id = record.user_id

    # An interesting quirk of the audit log is that it does not record when you delete your own message.
    # So, if we cannot find the moderator ID, we assume the deleter is the author themselves.

    if not mod_id:
        embed = (
            hikari.Embed(
                title="Message Deleted",
                description=f"{event.old_message.author.mention} deleted their own message in <#{event.channel_id}>.",
                colour=0xff0000
            )
            .add_field(
                name="Old Message",
                value=f"\"{event.old_message.content}\""
            )
        )
    else:
        embed = (
            hikari.Embed(
                title="Message Deleted",
                description=f"{event.old_message.author.mention}'s message was deleted <#{event.channel_id}>.",
                colour=0xff0000
            )
            .add_field(
                name="Moderation Details",
                value=f"Moderator: <@{mod_id}>\nTimestamp: <t:{deletion_time.timestamp}:f>"
            )
            .add_field(
                name="Old Message",
                value=f"\"{event.old_message.content}\""
            )
        )

    await server_logs(event.guild_id).create_entry(embed)

# TODO: Re-Implement bulk-deletion tracking.