from modules.automod.commands.views.automod_modules_view import views
from modules.automod.commands.group import group
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="modules",
    description="Config menu for all the automod modules!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("list-modules", ctx, hikari.Permissions.ADMINISTRATOR)

        view = views(ctx.guild_id, ctx.user.id)
        embed = view.gen_embed()
        view_menu = view.init_view()

        resp = await ctx.respond(
            embed=embed,
            components=view_menu.build(),
        )
        view.ctx = ctx
        view.resp = resp

        miru_client.start_view(view_menu)
        await view_menu.wait()