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
    name="unban",
    description="Undo a ban for a member of the server!"
):
    
    target = lightbulb.user("target", "Who to Ban")
    reason = lightbulb.string("reason", "Why are they being banned?")
    hours_deletion = lightbulb.integer("delete_hours", "how many hours worth of their messages should be deleted?", min_value=0)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("unban_user", ctx, hikari.Permissions.BAN_MEMBERS)

        guild = dbguild(ctx.guild_id)

        success = await guild.bans.unban_user(
            user_id=self.target.id,
            mod_id=ctx.user.id,
            reason=self.reason,
        )

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Member Unbanned!",
                    description=f"User has been pardoned from their ban.",
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