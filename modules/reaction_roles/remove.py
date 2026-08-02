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
    name="remove",
    description="Remove a reaction role!"
):
    
    emoji = lightbulb.string("emoji", "What emoji was used for the reaction role?")
    group_id = lightbulb.string("group_id", "The group ID to be removed from")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("rrg remove role", ctx, hikari.Permissions.MANAGE_ROLES)

        try:
            rrg = rr_group(self.group_id)
        except rr_errors.UngroupedMessage:
            await ctx.respond(
                hikari.Embed(
                    title="Not Grouped",
                    description=(
                        "The reaction role group you referred to does not exist.\n"
                        "To resolve this, please run `/reactionroles new` and create a group!"
                    )
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        try:
            rr_item = rrg.fetch_item(self.emoji)
            success = rrg.rm_item(emoji=self.emoji)
        except rr_errors.ItemNotFound:
            await ctx.respond(
                hikari.Embed(
                    title="Not Found",
                    description="This reaction role group could not be found."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return
        except rr_errors.EmojiNotPresent:
            await ctx.respond(
                hikari.Embed(
                    title="Reaction Role Not Present",
                    description="This reaction role doesn't exist to be removed."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Reaction Role Removed",
                    description=f"This reaction role group now has had {self.emoji} removed as a reaction role"
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )

            await server_logs(ctx.guild_id).create_entry(
                hikari.Embed(
                    title="Reaction-Role Removed",
                    description=f"{ctx.user.mention} Has removed the reaction role <@&{rr_item.reaction_role_id}> from reaction-role group {self.group_id}",
                    colour=0xFFA500
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Reaction role error!",
                    description="I was unable to remove this reaction role. It may be a bug on our side."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )