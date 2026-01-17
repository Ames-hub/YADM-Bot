from library.database.guilds import muting, dbguild
from library import datastore as ds
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def task() -> None:
    all_mutes = muting.list_all_mutes()

    for case_id in all_mutes:
        mute_case = all_mutes[case_id]

        muted_user = mute_case['user_id']
        scheduled_unmute = mute_case['scheduled_unmute']

        now = datetime.now().timestamp()
        if now <= scheduled_unmute:
            guild_id = mute_case['guild_id']

            guild = dbguild(guild_id)
            guild_mute_role = guild.get.muted_role_id()

            unmute_failure = False
            try:
                await botapp.rest.remove_role_from_member(
                    guild=guild_id,
                    user=muted_user,
                    role=guild_mute_role
                )
            except (hikari.ForbiddenError, hikari.NotFoundError):
                unmute_failure = True

            guild_name = ds.d["guild_name_cache"].get(int(guild_id), None).get('name', None)
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
                        title="🔈 Unmuted (!)",
                        description=f"We attempted to unmute you in *{guild_name}*,\n"
                        "but it seems we do not have permission by the server owners to do so."
                    )
                    .add_field(
                        name="Recommendation",
                        value="Send a screenshot of this message (or forward this message) to the admins as proof that your mute is over.\n"
                        f"(The mute with the ID {case_id} has now expired, and this user should be unmuted.)"
                    )
                )

            # TODO: have this send an embed to the logs channel too

            try:
                user = await botapp.rest.fetch_user(muted_user)
                await user.send(embed)
            except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                return True