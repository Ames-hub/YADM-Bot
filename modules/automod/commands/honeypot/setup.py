from modules.automod.commands.honeypot.subgroup import honeypot_subgroup
from modules.automod.commands.views.honeypot_view import views
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari

loader = lightbulb.Loader()

@honeypot_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="setup",
    description="Setup the spam-bot honey-pot for your server"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("honeypot setup", ctx, hikari.Permissions.ADMINISTRATOR)

        view = views(ctx.guild_id, mod_id=ctx.user.id, ctx=ctx)
        embed = view.gen_embed(go_ahead_okayed=False)
        view_menu = view.init_view()

        resp = await ctx.respond(
            embed=embed,
            components=view_menu.build(),
        )
        view.ctx = ctx
        view.resp = resp

        miru_client.start_view(view_menu)
        await view_menu.wait()