from modules.moderation.views.purge_view import views
from modules.moderation.group import group
from datetime import datetime, timedelta
from library.botapp import miru_client
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_channel_purge():
    pass

@group.register
class command(
    lightbulb.SlashCommand,
    name="purge",
    description="Purge messages from a channel!"
):
    
    channel = lightbulb.channel("channel", "Which channel to purge")
    reason = lightbulb.string("reason", "Reason for purging messages", default="No reason provided.")
    purge_days = lightbulb.integer("days", "How many days worth of messages to purge?", min_value=0, default=0)
    purge_hours = lightbulb.integer("hours", "How many hours worth of messages to purge?", min_value=0, default=0)
    purge_minutes = lightbulb.integer("minutes", "How many minutes worth of messages to purge?", min_value=0, default=0)
    purge_seconds = lightbulb.integer("seconds", "How many seconds worth of messages to purge?", min_value=0, default=0)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_MESSAGES, ctx)

        if self.purge_days == 0 and self.purge_hours == 0 and self.purge_minutes == 0 and self.purge_seconds == 0:
            await ctx.respond(
                hikari.Embed(
                    title="Invalid Duration",
                    description=(
                        "You must specify a duration for purging messages. "
                        "Please provide at least one of the following: days, hours, minutes, or seconds."
                    ),
                    colour=0xFFA500
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        delete_after = datetime.now() - timedelta(
            days=self.purge_days,
            hours=self.purge_hours,
            minutes=self.purge_minutes,
            seconds=self.purge_seconds
        )

        if delete_after < datetime.now() - timedelta(days=14):
            await ctx.respond(
                hikari.Embed(
                    title="Too Far Back!",
                    description=(
                        "Sorry, you cannot purge messages older than 14 days due to Discord limitations.\n"
                        "Please specify a more recent duration."
                    ),
                    colour=0xFFA500
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        view = views(
            guild_id=ctx.guild_id,
            delete_after=delete_after,
            channel=self.channel.id,
            reason=self.reason
        )
        embed = view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()