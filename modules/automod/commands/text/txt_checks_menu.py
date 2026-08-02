from modules.automod.commands.views.automod_txt_checks_view import views
from modules.automod.commands.text.subgroup import text_subgroup
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="checks",
    description="Menu for toggling which of the automod's checks are running."
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("text-am-menu", ctx, hikari.Permissions.ADMINISTRATOR)

        view = views(ctx.guild_id)
        embed = view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()