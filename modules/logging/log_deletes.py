from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
from modules.logging.group import group
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="msg_deletion",
    description="Set whether or not we log message deletions!"
):
    
    do_log_deletions = lightbulb.boolean("enabled", "Log message deletions?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("log-msg-deletion", ctx, [hikari.Permissions.VIEW_AUDIT_LOG, hikari.Permissions.MANAGE_MESSAGES])

        guild = dbguild(ctx.guild_id)
        success = guild.logs_config.msg_deletions.toggle_logging(bool(self.do_log_deletions))

        if success:
            embed = hikari.Embed(
                title="Settings changed",
                description="Whenever a message is deleted, it'll be sent to the designated logging channel."
            )
            if guild.logs_config.get_logs_channel() is None:
                embed.add_field(
                    name="No logging channel!",
                    value="Please set one using `/moderation livelog channel` command.",
                )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Deletion Logging Enabled",
                    description=(
                        f"On {datetime.now().strftime('%Y-%b-%d %I:%M %p')}, "
                        f"the bot was told to {'not log deleted messages' if not self.do_log_deletions else 'log deleted messages'}.\n\n"
                        f"Order issued by <@{ctx.user.id}>."
                    ),
                    colour=0xFF0000 if not self.do_log_deletions else 0x00FF00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Uh oh!",
                    description="Something didn't go quite right, please try again later."
                )
            )