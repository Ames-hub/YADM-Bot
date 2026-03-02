from modules.utility.views.setup_view import views
from library.database.guilds import dbguild
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.command
class command(
    lightbulb.SlashCommand,
    name="setup",
    description="Set the bot to use the recommended bot settings!"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
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