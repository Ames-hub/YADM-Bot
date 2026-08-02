from library.database.auditing import server_logs
from modules.moderation.group import group
from library.permissions import prechecks
from library.botapp import botapp
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="unlock",
    description="Unlock a channel!"
):
    
    channel = lightbulb.channel("channel", "Which channel to unlock")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("channel unlock", ctx, hikari.Permissions.MANAGE_CHANNELS)

        await server_logs(ctx.guild_id).create_entry(
            hikari.Embed(
                title="Channel Unlock",
                description=f"On {datetime.now().strftime('%Y-%b-%d %I:%M %p')} <#{self.channel}> has been unlocked by <@{ctx.user.id}>.",
                colour=0x00FF00
            )
        )
        
        try:
            await botapp.rest.edit_permission_overwrite(
                channel=self.channel.id,
                target_type=hikari.PermissionOverwriteType.ROLE,
                target=ctx.guild_id,
                allow=hikari.Permissions.SEND_MESSAGES,
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            await ctx.respond(
                hikari.Embed(
                    title="Unlock Failed",
                    description=(
                        "I was unable to unlock that channel. Please ensure I have the 'Manage Channels' permission and try again.\n"
                        "If you believe I have the correct permissions, please contact support."
                    ),
                    colour=0xFF0000
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return
        except hikari.NotFoundError:
            await ctx.respond(
                hikari.Embed(
                    title="Channel Not Found",
                    description="I couldn't find that channel. Please ensure you provided a valid channel and try again.",
                    colour=0xFF0000
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        locked_embed = hikari.Embed(
            title="🔓 Channel Unlocked 🔓",
            description=f"This channel has been unlocked by <@{ctx.user.id}>.",
            colour=0x00FF00
        )

        if ctx.channel_id == self.channel.id:
            await ctx.respond(
                locked_embed
            )
            return
        else:
            send_success = True
            try:
                await botapp.rest.create_message(
                    self.channel.id,
                    locked_embed
                )
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                send_success = False

            resp_embed = hikari.Embed(
                title="Channel Unlocked",
                description="We've unlocked that channel, and have announced that the channel is unlocked in that channel too.",
                colour=0x00FF00
            )
            if not send_success:
                resp_embed.add_field(
                    name="⚠️ Announcement Failed",
                    value=(
                        "I was unable to send a message in that channel to announce the unlock.\n"
                        "Please ensure I have permission to send messages in that channel so that users are aware of the unlock."
                    ),
                )

            await ctx.respond(resp_embed, flags=hikari.MessageFlag.EPHEMERAL)