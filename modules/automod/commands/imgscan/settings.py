from modules.automod.commands.views.automod_penalties_view import views
from modules.automod.commands.imgscan.subgroup import imgscan_subgroup
from library.automod import automod_types
from library.botapp import miru_client
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@imgscan_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="settings",
    description="Menu for changing your automod's image filtering settings!"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        view = views(ctx.guild_id, automod_category=automod_types.IMAGE_FILTER)
        embed = view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
            flags=hikari.MessageFlag.EPHEMERAL
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()