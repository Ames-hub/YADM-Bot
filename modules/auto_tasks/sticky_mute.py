from library.database.auditing import server_logs
from library.database.guilds import dbguild, muting
from datetime import datetime, timedelta
from library import datastore as ds
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

@botapp.listen(hikari.events.MemberCreateEvent)
async def listener(event: hikari.events.MemberCreateEvent):
    """
    It occurs to me that people can get rid of a mute by leaving and joining a guild.
    This listens for user's who've left that have an active mute, and reapplies their mute role if they rejoin. 
    """
    guild = dbguild(event.guild_id)
    # Exclude cooldowns because it'd probably take the time of a cooldown to leave and rejoin a guild.
    is_muted = guild.muting.get_is_muted(event.member.id, exclude_cooldowns=True)

    if is_muted:
        mute_role = guild.get.muted_role_id()
        if not mute_role:
            await server_logs(event.guild_id).create_entry(
                hikari.Embed(
                    title="Mute Role Not Set",
                    description=f"Tried to re-mute <@{event.member.id}> but the mute role was not set for the bot."
                )
            )
            return

        mute_case = guild.muting.get_mute()
        # Checks if there's less than 30 seconds until they're meant to be unmuted.
        if (mute_case.scheduled_unmute - (datetime.now() - timedelta(seconds=30))) > datetime.now().timestamp():
            # Removes the mute if the unmute is super soon anyway.
            muting.set_mute_inactive(mute_case.case_id)
            return

        try:
            await event.app.rest.add_role_to_member(
                guild=event.guild_id,
                user=event.member.id,
                role=mute_role,
                reason="User left while an active mute was applied, perhaps trying to evade the mute."
            )
        except hikari.NotFoundError:
            await server_logs(event.guild_id).create_entry(
                hikari.Embed(
                    title="Mute Role Not Found",
                    description=f"Tried to re-mute <@{event.member.id}> but the mute role did not seem to exist, or we don't have access to it."
                )
            )
            return
        except hikari.ForbiddenError:
            await server_logs(event.guild_id).create_entry(
                hikari.Embed(
                    title="Permissions Error",
                    description=f"Tried to re-mute <@{event.member.id}> but we're lacking access to apply the mute role."
                )
            )
            return

        await server_logs(event.guild_id).create_entry(
            hikari.Embed(
                title="MUTE EVASION 🚨",
                description=f"We detected that user <@{event.member.id}> Attempted to leave and rejoin the server while a mute was active!"
            )
            .add_field(
                name="What's this mean?",
                value=(
                    "It likely means that the user tried to exploit the fact that leaving a server gets rid of all your roles, like the muted role.\n"
                    "This would result in an early unmute. We have re-applied the mute role to combat this."
                )
            )
        )
        return