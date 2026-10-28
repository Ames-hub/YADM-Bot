from modules.moderation.views.profile_view import views
from modules.moderation.group import group
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="profile",
    description="Have the bot compile a full profile on a user"
):
    
    target_user = lightbulb.user("user", "Who do we compile data on?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("moderation profile", ctx, hikari.Permissions.MANAGE_MESSAGES)

        # TODO: Make this track if the member ever was muted or banned in the past in the server.

        view = views(
            author_id=ctx.user.id,
            guild_id=ctx.guild_id,
            target_user=self.target_user,
        )
        embed = await view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()