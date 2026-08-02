from modules.automod.commands.views.automod_penalties_view import views
from modules.automod.commands.text.subgroup import text_subgroup
from library.automod import automod_types
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="settings",
    description="Menu for changing your automod's text filtering settings!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("text-am-settings", ctx, hikari.Permissions.ADMINISTRATOR)

        view = views(ctx.guild_id, automod_types.TEXT_FILTER)
        embed = view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()