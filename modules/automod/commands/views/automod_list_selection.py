from library.database.auditing import server_logs
from library.database.guilds import dbguild
import hikari
import miru

class views:
    def __init__(self, guild_id:int, mod_id:int):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.mod_id = mod_id

        # 🔹 Ensure guild row exists before doing anything else
        if not self.guild.exists_in_db():
            self.guild.create()

        self.refresh_automod_data()

    def refresh_automod_data(self):
        self.use_swears_list = self.guild.get.text.use_preset_swears_list()
        self.use_slurs_list = self.guild.get.text.use_preset_slurs_list()
        self.use_lessnsfw_list = self.guild.get.text.use_preset_lessnsfw_list()
        self.use_hardnsfw_list = self.guild.get.text.use_preset_hardnsfw_list()
        return True

    def gen_embed(self, no_refresh:bool=False):
        if not no_refresh:
            self.refresh_automod_data()

        enabled = self.guild.get.do_text_scan()
        if not enabled:
            disabled_warning = " — Module Disabled"
        else:
            disabled_warning = ""

        embed = hikari.Embed(
            title=f"Text Automod Word Config{disabled_warning}",
            description="The below lets you select what category of words are banned\n\n",
            color=0x00ffff
        )

        embed.add_field(
            name="Swear Words?",
            value="✅ Text filter Will delete swears" if self.use_swears_list else "❌ Text filter will allow swearing",
            inline=False
        )
        embed.add_field(
            name="Slurs",
            value="✅ Text filter Will delete slurs" if self.use_slurs_list else "❌ Text filter will allow slurs",
            inline=False
        )
        embed.add_field(
            name="Soft-NSFW Words",
            value="✅ Border-line NSFW Words will be deleted." if self.use_lessnsfw_list else "❌ Border-line NSFW words will not be deleted.",
            inline=False
        )
        embed.add_field(
            name="Hard-NSFW Words",
            value="✅ Words that are definitely NSFW will be deleted" if self.use_hardnsfw_list else "❌ Will not delete NSFW words",
            inline=False
        )

        return embed

    def init_view(viewself):
        viewself.refresh_automod_data()  # Always sync first

        active_style = hikari.ButtonStyle.PRIMARY
        inactive_style = hikari.ButtonStyle.SECONDARY

        class Menu_Init(miru.View):

            @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, row=4)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                await ctx.edit_response(
                    hikari.Embed(
                        title="Exitting menu.",
                        description="Your settings have been saved.",
                    ),
                    components=[]
                )
                self.stop()

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
                label="Delete Swear Words",
                style=active_style if viewself.use_swears_list else inactive_style,
                row=1
            )
            async def toggle_swears(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                active = not viewself.use_swears_list
                viewself.use_swears_list = active
                viewself.guild.set.text.use_preset_swears_list(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"Filter Settings Changed",
                        description=(
                            "Swear words will now be filtered for by the text filter." if active else "Swear words will no longer be filtered for."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Delete Slurs",
                style=active_style if viewself.use_slurs_list else inactive_style,
                row=1
            )
            async def toggle_slurs(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                active = not viewself.use_slurs_list
                viewself.use_slurs_list = active
                viewself.guild.set.text.use_preset_slurs_list(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"Filter Settings Changed",
                        description=(
                            "Slurs will now be filtered for by the text filter" if active else "Slurs will no longer be filtered for by the text filter"
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Delete Soft-NSFW",
                style=active_style if viewself.use_lessnsfw_list else inactive_style,
                row=1
            )
            async def toggle_softnsfw(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                active = not viewself.use_lessnsfw_list
                viewself.use_lessnsfw_list = active
                viewself.guild.set.text.use_preset_lessnsfw_list(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"Filter Settings Changed",
                        description=(
                            "Soft-NSFW words will now be filtered for by the text filter." if active else "Soft-NSFW Words will now be permitted."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Delete Hard-NSFW",
                style=active_style if viewself.use_hardnsfw_list else inactive_style,
                row=1
            )
            async def toggle_hard_nsfw(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                active = not viewself.use_hardnsfw_list
                viewself.use_hardnsfw_list = active
                viewself.guild.set.text.use_preset_hardnsfw_list(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"Filter Settings Changed",
                        description=(
                            "Hard-NSFW will now be filtered for by the text filter" if active else "Hard-NSFW will no longer be filtered for by the text filter"
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

        return Menu_Init(timeout=60)