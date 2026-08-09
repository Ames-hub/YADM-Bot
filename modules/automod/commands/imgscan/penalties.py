from modules.automod.commands.views.automod_penalties_view import views
from modules.automod.commands.imgscan.subgroup import imgscan_subgroup
from library.automod import automod_types
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@imgscan_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="penalties",
    description="Menu for changing your automod's image filtering penalties!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("img-am-settings", ctx, hikari.Permissions.ADMINISTRATOR)

        view = views(ctx.guild_id, automod_category=automod_types.IMAGE_FILTER, mod_id=ctx.user.id)
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