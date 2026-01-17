from modules.automod.commands.views.automod_menu_view import views
from modules.automod.commands.group import group
from library.botapp import miru_client
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="menu",
    description="Automoderation configuration menu"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

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