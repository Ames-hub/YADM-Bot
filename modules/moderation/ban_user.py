from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import prechecks
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="ban",
    description="Ban a member of the server!"
):
    
    target = lightbulb.user("target", "Who to Ban")
    reason = lightbulb.string("reason", "Why are they being banned?")
    hours_deletion = lightbulb.integer("delete_hours", "how many hours worth of their messages should be deleted?", min_value=0)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("ban_user", ctx, hikari.Permissions.BAN_MEMBERS)

        guild = dbguild(ctx.guild_id)
        del_seconds = self.hours_deletion * 3600

        success = await guild.bans.ban_user(
            banned_id=self.target.id,
            moderator_id=ctx.user.id,
            msg_del_seconds=del_seconds,
        )

        unban_timestamp = int(datetime.now().timestamp() - del_seconds)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Member Banned!",
                    description=f"User has been banned until <t:{unban_timestamp}:f>",
                    colour=0xff0000
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Ban Failed!",
                    description="Sorry, for some reason we could not ban them.",
                    colour=0xff0000
                )
            )