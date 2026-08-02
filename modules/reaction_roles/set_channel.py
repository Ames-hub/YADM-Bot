from library.database.reaction_roles import rr_group, rr_errors
from library.database.auditing import server_logs
from modules.reaction_roles.group import group
from library.permissions import prechecks
import lightbulb
import hikari
import re

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="channel",
    description="Update a reaction role group's channel!"
):
    
    group_id = lightbulb.integer("group_id", "The reaction roles group ID")
    channel = lightbulb.channel("channel", "The channel to assign to this group ID")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("set rrg channel", ctx, hikari.Permissions.MANAGE_ROLES)

        try:
            rrg = rr_group(self.group_id)
        except rr_errors.UngroupedMessage:
            await ctx.respond(
                hikari.Embed(
                    title="Not Grouped",
                    description=(
                        "The reaction role group you referred to does not exist.\n"
                        "To resolve this, please run `/reactionroles new` and create a group!"
                    ),
                    colour=0xff0000
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return
        
        success = rrg.set_channel(self.channel.id)
        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Channel set",
                    description=f"When you publish this reaction role group, it will now be published in {self.channel.mention}",
                    colour=0x00ff00
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )

            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Reaction-Role Channel",
                    description=f"{ctx.user.mention} Has set the channel for reaction role group {self.group_id} to {self.channel.mention}",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Channel not set",
                    description="We encountered a bug trying to set this channel. Please file a report!",
                    colour=0xff0000
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )