from library.database.reaction_roles import create_group
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
    name="new",
    description="create a new reaction role group!"
):
    
    embed_title = lightbulb.string("embed_title", "The title to give to the embed for the reaction roles", default=None)
    embed_desc = lightbulb.string("embed_desc", "The description to give to the embed", default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("new rr group", ctx, permission=hikari.permissions.MANAGE_ROLES)

        group_id = await create_group(
            guild_id=ctx.guild_id,
            channel_id=ctx.channel_id,
            embed_title=self.embed_title.strip(),
            embed_desc=self.embed_desc.strip()
        )

        if group_id is False:
            await ctx.respond(
                hikari.Embed(
                    title="Failure!",
                    description="Couldn't create the group, this is a bug!"
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        await ctx.respond(
            hikari.Embed(
                title=f"Group Created - {group_id}",
                description=f"A new group has been created, and linked to this channel under the **ID: {group_id}**"
            )
            .add_field(
                name="Getting started",
                value="Add some reaction roles with `/reactionrole add` and then run `/reactionrole publish` to send the reaction role out"
            ),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        await server_logs(ctx.guild_id).create_entry(
            hikari.Embed(
                title="New Reaction-Role Group",
                description=f"{ctx.user.mention} Has created a new reaction role group, titled \"{self.embed_title}\"",
                colour=0x00ff00
            )
        )