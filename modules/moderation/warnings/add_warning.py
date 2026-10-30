from modules.moderation.warnings.subgroup import warnings_group
from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from library import datastore as ds
from library.botapp import botapp
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

@warnings_group.register
class command(
    lightbulb.SlashCommand,
    name="issue",
    description="Give an official warning to someone for what they're doing"
):
    
    target_user = lightbulb.user("target", "Who to warn")
    reason = lightbulb.string("reason", "What did they do?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("add warning", ctx, hikari.Permissions.MANAGE_MESSAGES)
        guild = dbguild(ctx.guild_id)

        warn_id = guild.warnings.add_warning(
            reason=self.reason,
            mod_id=self.moderator.id,
            user_id=self.target_user.id,
        )

        cache_expire_time = 86400  # 1 day in seconds
        timestamp_now = datetime.datetime.now().timestamp()

        # Check our cache for the guild's name
        cache_obj = ds.d["guild_name_cache"].get(int(ctx.guild_id), None)
        if cache_obj:
            if not timestamp_now - cache_obj['time'] >= cache_expire_time:
                guild_name = cache_obj['name']
            else:
                guild_name = None
        else:
            guild_name = None

        if not guild_name:
            # Get from discord, add to cache.
            discord_guild = await botapp.rest.fetch_guild(int(ctx.guild_id))
            ds.d["guild_name_cache"][int(ctx.guild_id)] = {"name": discord_guild.name, "time": timestamp_now}
            guild_name = discord_guild.name

        warn_embed = (
            hikari.Embed(
                title=f"⚠️ Warning Received! (#{warn_id})",
                description=f"You were warned by '{guild_name}' trust & safety team for the following reason:\n{self.reason}",
                colour=0xff0000
            )
        )

        if warn_id is not False:
            notify_okay = True
            try:
                await self.target_user.send(warn_embed)
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                notify_okay = False

            embed = hikari.Embed(
                title="Warn Notice ⚠️",
                description=f"A Record of warning under ID {warn_id} has been added to this user."
            )
            if not notify_okay:
                embed.add_field(
                    name="No Notification",
                    value=f"{self.user.mention} Wasn't able to be notified of their warning."
                )

            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Warning Issued!",
                    description=f"{self.target_user.mention} was warned by the server trust & safety moderator, {ctx.user.mention}.",
                    colour=0xffff00
                )
                .add_field(
                    name="Reason Provided",
                    value=f"\"{self.reason}\""
                )
                .set_footer(f"Warning under ID {warn_id}")
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="Couldn't warn this user for some reason!"
                )
            )
