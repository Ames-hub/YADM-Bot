from library.database.guilds import muting, dbguild
from library.database.auditing import server_logs
from library import datastore as ds
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_task():
    all_mutes = muting.list_all_mutes(active_only=True)

    for mute_case in all_mutes:
        now = datetime.now().timestamp()
        if now >= mute_case.scheduled_unmute:
            guild_id = mute_case.guild_id

            guild = dbguild(guild_id)
            guild_mute_role = guild.get.muted_role_id()

            unmute_failure = False
            try:
                await botapp.rest.remove_role_from_member(
                    guild=guild_id,
                    user=mute_case.user_id,
                    role=guild_mute_role
                )
                muting.set_mute_inactive(mute_case.case_id)
            except (hikari.ForbiddenError, hikari.NotFoundError):
                unmute_failure = True

            guild_name = ds.d["guild_name_cache"].get(int(guild_id), {}).get('name')
            if not guild_name:
                try:
                    discord_guild = await botapp.rest.fetch_guild(guild_id)
                    guild_name = discord_guild.name
                    ds.d["guild_name_cache"][int(guild_id)] = {"name": discord_guild.name, "time": datetime.now().timestamp()}
                except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                    guild_name = None

            if not guild_name:
                return  # No guild name available. No point in notifying.
            
            if not unmute_failure:
                embed = (
                    hikari.Embed(
                        title="🔈 Unmuted",
                        description=f"You have been muted in {guild_name}"
                    )
                )
            else:
                embed = (
                    hikari.Embed(
                        title="🔈 Unmuted (problem!)",
                        description=f"We attempted to unmute you in *{guild_name}*,\n"
                        "but it seems we do not have permission by the server owners to do so."
                    )
                    .add_field(
                        name="Recommendation",
                        value="Send a screenshot of this message (or forward this message) to the admins as proof that your mute is over.\n"
                        f"(The mute with the ID {mute_case.case_id} has now expired, and this user should be unmuted.)"
                    )
                )

            try:
                user = await botapp.rest.fetch_user(mute_case.user_id)
            except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                log_embed = (
                    hikari.Embed(
                        title="Member Unmuted",
                        description=f"<@{mute_case.user_id}> Has been unmuted as of <t:{mute_case.scheduled_unmute}:R>"
                    )
                )

                server_logs(mute_case.guild_id).create_entry(log_embed)
                continue

            log_embed = (
                hikari.Embed(
                    title="Member Unmuted",
                    description=f"{user.mention} ({user.username}) Has been unmuted as of <t:{int(mute_case.scheduled_unmute)}:R>",
                    colour=0x00ff00
                )
                .add_field(
                    name="Original Mute Reason",
                    value=f"The user was muted originally by {mute_case.moderator_id} for:\n\"{mute_case.reason}\""
                )
            )

            await server_logs(mute_case.guild_id).create_entry(log_embed)

            try:
                await user.send(embed)
            except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                continue

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False), auto_start=True)
async def task() -> None:
    await handle_task()