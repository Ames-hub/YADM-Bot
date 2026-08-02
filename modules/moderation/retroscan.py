from modules.moderation.views.retroscan_view import views
from library.database.guilds import dbguild
from modules.moderation.group import group
from library.permissions import prechecks
from library.botapp import miru_client
import lightbulb
import hikari


loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="retroscan",
    description="Retro-actively scan a channel through the automod."
):
    
    penalize = lightbulb.boolean("penalize", "Should we issue penalties to prior rule breakers?")
    channel = lightbulb.channel("channel", "Which channel to scan", default=None)
    hours_back = lightbulb.integer("hours_back", "How many hours back should we look?", default=335)  # Slightly under two weeks by default

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:

        perms_needed = [hikari.Permissions.MANAGE_MESSAGES, hikari.Permissions.MANAGE_GUILD]
        guild = dbguild(ctx.guild_id)
        do_kick = guild.get.text.do_kick_member()
        if do_kick:
            perms_needed.append(hikari.Permissions.KICK_MEMBERS)
        do_ban = guild.get.text.do_ban_member()
        if do_ban:
            perms_needed.append(hikari.Permissions.BAN_MEMBERS)
        await prechecks("retroscan", ctx, perms_needed, auto_defer=False)

        if self.channel is None:
            self.channel = ctx.channel_id
        else:
            self.channel = self.channel.id

        view = views(
            guild_id=ctx.guild_id,
            do_kick=do_kick,
            do_ban=do_ban,
            penalize=self.penalize,
            channel=self.channel,
            hours_back=self.hours_back,
            mod_id=ctx.user.id
        )
        embed = view.gen_embed()
        view_menu = view.init_view()

        await ctx.respond(
            embed=embed,
            components=view_menu.build(),
        )

        miru_client.start_view(view_menu)
        await view_menu.wait()