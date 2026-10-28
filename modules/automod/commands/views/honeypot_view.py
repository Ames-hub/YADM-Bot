from library.database.auditing import server_logs
from library.database.honeypot import honeypot
from library.database.guilds import dbguild
import lightbulb
import hikari
import miru

class views:
    def __init__(self, guild_id, mod_id, ctx: lightbulb.Context):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.mod_id = mod_id
        self.ctx = ctx

    def gen_embed(self, go_ahead_okayed:bool):
        if not go_ahead_okayed:
            embed = (
                hikari.Embed(
                    title=f"Anti-bot Honeypot",
                    description=(
                        "This is a feature for catching compromised accounts used in spam networks, and just in general spam bots."
                    ),
                    colour=0x00ffff
                )
                .add_field(
                    name="What's a Honeypot?",
                    value=(
                        "A Honeypot is a trap. How it works is that we create a channel called 'not general' or 'spampot' or something like that "
                        "with the default behavior being that whoever sends a message in that channel is instantly banned, or muted, or whatever. "
                        "What this does is that when a spam bot joins and attempts to spam in every channel, it'll quickly fall into the honey-pot by "
                        "sending a message in the honey-pot channel. This flags the account, and lets us know to handle the spam bot however you decide."
                    )
                )
            )

            pot = honeypot(self.guild_id)
            honeypot_channel = pot.get_channel()
            if honeypot_channel is not None:
                embed.add_field(
                    name="Honeypot already setup?",
                    value=(
                        "Our logs show there's already a honeypot channel created, "
                        "are you sure you don't want to just enable it instead of make a new one?"
                    )
                )
        else:
            embed = (
                hikari.Embed(
                    title=f"Honeypot Confirmed",
                    description=(
                        "We're now in the process of setting up a honey-pot. Do not send any messages into the channel we're creating."
                    ),
                    colour=0x00ffff
                )
            )

        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            async def on_timeout(self) -> None:
                await viewself.ctx.edit_response(
                    viewself.resp,
                    embed=hikari.Embed(
                        title="Menu Exitted",
                        description="This menu has closed itself after being left open for too long."
                    ),
                    components=[]
                )

            @miru.button(
                label="Confirm Setup",
                emoji="⚠️",
                style=hikari.ButtonStyle.PRIMARY,
            )
            async def confirm_do_setup(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.author.id != viewself.mod_id:
                    return

                await ctx.edit_response(viewself.gen_embed(go_ahead_okayed=True), components=[])
                self.stop()
                await viewself.guild.honeypot.setup()
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Honeypot 🍯",
                        description=f"<@{viewself.mod_id}> has authorised setting up a honey-pot for spam-bots and compromised accounts.",
                        colour=0xffff00
                    )
                )

            @miru.button(
                label="Cancel",
                emoji="❌",
                style=hikari.ButtonStyle.SECONDARY,
            )
            async def cancel_setup(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.author.id != viewself.mod_id:
                    return

                await ctx.edit_response(viewself.gen_embed(go_ahead_okayed=False), components=[])
                await self.stop()

        return Menu_Init(timeout=60)