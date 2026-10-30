from library.database.guilds import dbguild, violations
from library.database.auditing import server_logs
from library import datastore as ds
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.BanCreateEvent)
async def botfunction(event: hikari.events.BanCreateEvent):
    try:
        ban_data = await event.fetch_ban()
    except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
        await server_logs(guild_id=event.guild_id).create_entry(
            hikari.Embed(
                title="Bans Permission Error",
                description=(
                    "When attempting to fetch a ban made without the bot's help, "
                    "Discord blocked us from fetching it. "
                    "Do we have sufficient permissions to do so?"
                ),
                colour=0xff0000
            )
        )
        return

    # Reads from the audit log to find the moderator
    try:
        entries = await botapp.rest.fetch_audit_log(
            guild=event.guild_id,
            event_type=hikari.AuditLogEventType.MEMBER_BAN_ADD,
        )
    except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
        await server_logs(guild_id=event.guild_id).create_entry(
            hikari.Embed(
                title="Bans Permission Error",
                description=(
                    "When attempting to fetch a ban made without the bot's help, "
                    "Discord blocked us from fetching it. "
                    "Do we have permission to read the server audit logs?"
                ),
                colour=0xff0000
            )
        )
        return

    reason = ban_data.reason
    moderator_id = None
    for auditlog in entries:
        for snowflake, record in auditlog.entries.items():
            if not record.target_id == event.user_id:
                continue

            if record.reason != reason:
                # If its not the same reason, then it can't be the same ban.
                continue
            # banned would be record.target_id, so this is hopefully the moderator.
            moderator_id = record.user_id

    if moderator_id is None:
        # This can't be None.
        return False

    mod_name = ds.d["all_users_talking"].get(moderator_id, None)
    if not mod_name:
        try:
            moderator = await botapp.rest.fetch_user(moderator_id)
        except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
            return
        mod_name = moderator.display_name

    infraction_id = violations.create_member_violation(
        guild_id=event.guild_id,
        reporter_id=moderator_id,
        reporter_name=mod_name,
        offender_id=ban_data.user.id,
        offender_name=ban_data.user.username,
        time=datetime.now(),
        violation=reason,
        automated=False,
        whistleblower="User-triggered",
    )

    guild = dbguild(event.guild_id)
    guild.bans.track_ban(
        infraction_id=infraction_id,
        banned_id=ban_data.user.id,
        moderator_id=moderator_id,
        # TODO: Make it configurable so that bans we don't control CAN also get unbanned eventually (by server config)
        time_to_unban=-1  # Discord controlled bans are permanent by default.
    )