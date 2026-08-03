from modules.moderation.warnings.subgroup import warnings_subgroup
from library.database.guilds import dbguild
from library.permissions import prechecks
from library import datastore as ds
from library.botapp import botapp
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

async def handle_warn_user(guild_id:int, user:hikari.User, reason:str, responder_func):
    guild = dbguild(guild_id)

    warn_id = guild.warnings.add_warning(
        reason=reason,
        mod_id=user.id,
        user_id=user.id
    )

    cache_expire_time = 86400  # 1 day in seconds
    timestamp_now = datetime.datetime.now().timestamp()

    # Check our cache for the guild's name
    cache_obj = ds.d["guild_name_cache"].get(int(guild_id), None)
    if cache_obj:
        if not timestamp_now - cache_obj['time'] >= cache_expire_time:
            guild_name = cache_obj['name']
        else:
            guild_name = None
    else:
        guild_name = None

    if not guild_name:
        # Get from discord, add to cache.
        discord_guild = await botapp.rest.fetch_guild(int(guild_id))
        ds.d["guild_name_cache"][int(guild_id)] = {"name": discord_guild.name, "time": timestamp_now}
        guild_name = discord_guild.name

    warn_embed = (
        hikari.Embed(
            title=f"⚠️ Warning Received! ({warn_id})",
            description=f"You were warned by '{guild_name}' administration for the following reason:\n{reason}"
        )
    )

    if warn_id is not False:
        notify_okay = True
        try:
            await user.send(warn_embed)
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
            notify_okay = False

        embed = hikari.Embed(
            title="Warn Notice ⚠️",
            description="A Record of warning has been added to this user."
        )
        if not notify_okay:
            embed.add_field(
                name="No Notification",
                value=f"{user.mention} Wasn't able to be notified of their warning."
            )

        await responder_func(embed)
    else:
        await responder_func(
            hikari.Embed(
                title="Error!",
                description="Couldn't warn this user for some reason!"
            )
        )

@warnings_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="add",
    description="Give an official warning to someone for what they're doing"
):
    
    user = lightbulb.user("target", "Who to warn")
    reason = lightbulb.string("reason", "What did they do?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("add warning", ctx, hikari.Permissions.ADMINISTRATOR)
        return await handle_warn_user(
            ctx.guild_id,
            self.user,
            self.reason,
            ctx.respond
        )