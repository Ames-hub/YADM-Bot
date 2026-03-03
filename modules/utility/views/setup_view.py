from library.database.auditing import server_logs
from library.database.guilds import dbguild
import hikari
import miru


class views:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)

    def gen_embed(self):
        embed = hikari.Embed(
            title="Over-write Settings Confirmation",
            description=(
                "Are you sure you want to use the bot recommended settings?\n"
                "This will over-write any existing settings you have configured for the bot."
            ),
            colour=0xFFA500
        )
        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await ctx.edit_response(
                    hikari.Embed(
                        title="Cancelled",
                        description="Setup over-write has been cancelled.",
                    ),
                    components=[]
                )
                self.stop()

            @miru.button(
                label="Confirm",
                style=hikari.ButtonStyle.SUCCESS,
                emoji="✅"
            )
            async def confirm(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await viewself.guild.set_recommended_settings()
                await ctx.edit_response(
                    hikari.Embed(
                        title="Success",
                        description="The bot has been set to use the recommended settings!",
                        color=0x00FF00
                    )
                    .add_field(
                        name="The following has changed",
                        value=(
                            "• Text scanning has been enabled\n"
                            "• Spam Protection has been enabled\n"
                            "• Image filtering has been enabled\n"
                            "• Text scanning will now a) announce infractions, b) delete messages, c) warn users, d) put users on cooldown.\n"
                            "• Spam protection will now a) announce infractions, b) delete messages, c) warn users, d) put users on cooldown.\n"
                            "• Image filtering will now a) announce infractions, b) delete messages, c) warn users, d) put users on cooldown.\n"
                            "• NSFW image scan threshold has been set to 95% Certainty before action taken\n"
                            "• The bot will now use the following ban lists: a) swear words, b) slurs, c) Hard-NSFW but will allow soft NSFW\n"
                            "• A logs channel has been created, and log archiving has been enabled!\n"
                        )
                    ),
                    components=[]
                )
                server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Setup Overwritten",
                        description=f"{ctx.user.mention} Has set the bot to use the recommended settings, over-writing all old settings!",
                        color=0x00FF00
                    )
                )
                self.stop()

        return Menu_Init()