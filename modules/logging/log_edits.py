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
    name="msg_edits",
    description="Set whether or not we log message edits!"
):
    
    do_log_edits = lightbulb.boolean("enabled", "Log message edits?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("log-msg-edits", ctx, [hikari.Permissions.VIEW_AUDIT_LOG, hikari.Permissions.MANAGE_MESSAGES])

        guild = dbguild(ctx.guild_id)
        success = guild.logs_config.msg_edits.toggle_logging(bool(self.do_log_edits))

        if success:
            embed = hikari.Embed(
                title="Settings changed",
                description="Whenever a message is editted, it'll be sent to the designated logging channel."
            )
            if guild.logs_config.get_logs_channel() is None:
                embed.add_field(
                    name="No logging channel!",
                    value="Please set one using `/moderation livelog channel` command.",
                )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Edit Logging Enabled",
                    description=(
                        f"On {datetime.now().strftime('%Y-%b-%d %I:%M %p')}, "
                        f"the bot was told to {'not log edits to messages' if not self.do_log_edits else 'log edits made to messages'}.\n\n"
                        f"Order issued by <@{ctx.user.id}>."
                    ),
                    colour=0xFF0000 if not self.do_log_edits else 0x00FF00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Uh oh!",
                    description="Something didn't go quite right, please try again later."
                )
            )