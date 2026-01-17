from modules.moderation.warnings.subgroup import warnings_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
from library import datastore as ds
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

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
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)

        warn_id = guild.warnings.add_warning(
            reason=self.reason,
            mod_id=ctx.user.id,
        )

        cache_expire_time = 86400  # 1 day in seconds
        timestamp_now = datetime.datetime.now().timestamp()
        if not guild_name:
            # Check our cache
            cache_obj = ds.d["guild_name_cache"].get(int(ctx.guild_id), None)
            if cache_obj:
                if not timestamp_now - cache_obj['time'] >= cache_expire_time:
                    guild_name = cache_obj['name']
        if not guild_name:
            # Get from discord, add to cache.
            discord_guild = await ctx.client.rest.fetch_guild(int(ctx.guild_id))
            ds.d["guild_name_cache"][int(ctx.guild_id)] = {"name": discord_guild.name, "time": timestamp_now}
            guild_name = discord_guild.name

        warn_embed = (
            hikari.Embed(
                title=f"Warning Received! ({warn_id})",
                description=f"You were warned by '{guild_name}' administration for the following reason:\n{self.reason}"
            )
        )

        notify_okay = True
        try:
            await self.user.send(warn_embed)
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
            notify_okay = False

        if warn_id:
            embed = hikari.Embed(
                title="Notice",
                description="This user has been warned."
            )
            if not notify_okay:
                embed.add_field(
                    name="No Notification",
                    value=f"{self.user.mention} Wasn't able to be notified of their warning."
                )

            await ctx.respond(embed)
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't warn this user for some reason!"
                )
            )