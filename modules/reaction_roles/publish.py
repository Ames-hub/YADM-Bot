from library.database.reaction_roles import rr_group, rr_errors
from library.database.auditing import server_logs
from modules.reaction_roles.group import group
from library.permissions import perms
import lightbulb
import hikari
import re

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="publish",
    description="From an existing reaction role group, send it to the assigned channel."
):
    
    group_id = lightbulb.string("group_id", "The reaction role group to publish")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_ROLES, ctx)

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

        origin_msg = await ctx.respond(
            hikari.Embed(
                title="Publishing!",
                description=(
                    f"Your reaction role group is now being compiled, and sent to <#{rrg.group.channel_id}> for any to see and use.\n"
                    "__Depending on the amount of roles, this may take a moment.__"
                ),
                colour=0x00ff00
            ),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        success = await rrg.publish()
        if success:
            await ctx.edit_response(
                origin_msg,
                hikari.Embed(
                    title="Published!",
                    description=f"Those reaction roles are now available in the linked channel at <#{rrg.channel_id}>!"
                ),
            )
        else:
            await ctx.edit_response(
                origin_msg,
                hikari.Embed(
                    title="Can't Publish!",
                    description="Couldn't publish the reaction roles, please check our permissions and try again."
                ),
            )