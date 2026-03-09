from library.database.reaction_roles import rr_group, rr_errors, get_emoji_type
from library.database.auditing import server_logs
from modules.reaction_roles.group import group
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="add",
    description="Add a new reaction role!"
):
    
    group_id = lightbulb.string("group_id", "The message ID to assign the reaction role to")
    role = lightbulb.role("role", "Which role to assign as the reaction role?")
    emoji = lightbulb.string("emoji", "What emoji to use for the reaction role?")
    description = lightbulb.string("description", "What to describe the reaction role as", default=None)
    allow_remove = lightbulb.boolean("allow_remove", "Can users un-react to remove the reaction role?", default=True)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_ROLES, ctx)

        emoji_data = get_emoji_type(self.emoji)
        emoji_type = emoji_data['type']
        if emoji_type == None:
            await ctx.respond(
                hikari.Embed(
                    title="Not an Emoji",
                    description="You must enter an emoji as the reaction role, not "
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

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

        is_custom = emoji_type == "custom"

        try:
            if is_custom:
                success = rrg.add_item(
                    emoji_id=emoji_data['id'],
                    emoji_name=emoji_data['name'],
                    is_animated=emoji_data['animated'],
                    reaction_role=self.role.id,
                    allow_remove=self.allow_remove,
                    description=self.description,
                )
            else:
                success = rrg.add_item(
                    emoji_id=emoji_data['emoji'],
                    emoji_name=emoji_data['emoji'],
                    is_animated=emoji_data['animated'],
                    reaction_role=self.role.id,
                    allow_remove=self.allow_remove,
                    description=self.description,
                )
        except rr_errors.ItemNotFound:
            await ctx.respond(
                hikari.Embed(
                    title="Not Found",
                    description="This reaction role group could not be found."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return
        except rr_errors.EmojiAlreadyAdded:
            await ctx.respond(
                hikari.Embed(
                    title="Reaction Role Existing",
                    description="This reaction role already exists. Please remove it before creating it, or it'll be a duplicate."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        if success:
            embed = hikari.Embed(
                title="Reaction Role Added",
                description=f"This reaction role group now has <@&{self.role.id}> under {self.emoji} as its reaction role"
            )
            if is_custom:
                embed.add_field(
                    name="Warning",
                    value=(
                        "Custom emoji's cannot be external to this server for me to use them.\n"
                        "*If you can see the emoji in this text, then I can use it!* Otherwise, please use a different emoji.\n\n"
                        "(To remove it if you can't see the emoji, use `/reactionroles remove`)"
                    )
                )
            await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Reaction role error!",
                    description="I was unable to add this reaction role. It may be a bug on our side."
                ),
                flags=hikari.MessageFlag.EPHEMERAL
            )