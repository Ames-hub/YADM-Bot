from library.database.guilds import dbguild
import hikari
import miru

class views:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.set_category = self.guild.set.text.checks
        self.get_category = self.guild.get.text.checks
        self.guild.set_automod_defaults()  # This only effects things IF no settings have been made already.
        self.refresh_automod_data()

    def refresh_automod_data(self):
        # Refresh all check states
        self.equality_check = self.get_category.equality_check()
        self.symbol_check = self.get_category.symbol_check()
        self.collapsed_check = self.get_category.collapsed_check()
        self.spacehack_check = self.get_category.spacehack_check()
        self.letter_stitch_check = self.get_category.letter_stitch_check()
        self.reverse_check = self.get_category.reverse_check()
        self.similarity_check = self.get_category.similarity_check()
        self.syntactic_analysis = self.get_category.syntactic_analysis()
        return True

    def gen_embed(self, no_refresh:bool=False):
        if not no_refresh:
            self.refresh_automod_data()

        # Check if the main text filter module is enabled
        text_filter_enabled = self.guild.get.do_text_scan()
        disabled_warning = " — Main Module Disabled" if not text_filter_enabled else ""

        embed = hikari.Embed(
            title=f"Text Filter Checks Configuration{disabled_warning}",
            description="Configure which text analysis checks are enabled.\n"
            "Toggle each check on/off using the buttons below.\n",
            colour=0x00ffff
        )

        # This may be useless. Yes, it most certainly is. But it makes the embed look decent :)
        active_checks = 0
        for check in [self.equality_check, self.symbol_check, self.collapsed_check,
                      self.spacehack_check, self.letter_stitch_check, self.reverse_check,
                      self.similarity_check, self.syntactic_analysis]:
            if check is True:
                active_checks += 1

        # Add fields for each check
        embed.add_field(
            name="Equality Check",
            value="✅ Enabled" if self.equality_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Symbol Check",
            value="✅ Enabled" if self.symbol_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Collapsed Check",
            value="✅ Enabled" if self.collapsed_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Spacehack Check",
            value="✅ Enabled" if self.spacehack_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Letter Stitch Check",
            value="✅ Enabled" if self.letter_stitch_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Reverse Check",
            value="✅ Enabled" if self.reverse_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Similarity Check",
            value="✅ Enabled" if self.similarity_check else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Syntactic Analysis",
            value="✅ Enabled" if self.syntactic_analysis else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name=f"{active_checks}/8 Active",
            value=f"{active_checks} checks are toggled on out of 8",
            inline=True
        )
        embed.set_footer(
            text="Checking the `/automod text manual` command may be of use to you"
        )

        return embed

    def init_view(viewself):
        viewself.refresh_automod_data()  # Always sync first

        active_style = hikari.ButtonStyle.SUCCESS
        inactive_style = hikari.ButtonStyle.SECONDARY

        class Menu_Init(miru.View):

            @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, row=3)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await ctx.edit_response(
                    hikari.Embed(
                        title="Exiting menu.",
                        description="Your text filter check settings have been saved.",
                    ),
                    components=[]
                )
                self.stop()

            @miru.button(
                label="Toggle Equality",
                style=active_style if viewself.get_category.equality_check() else inactive_style,
                row=0
            )
            async def toggle_equality_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.equality_check()
                viewself.set_category.equality_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Symbol",
                style=active_style if viewself.get_category.symbol_check() else inactive_style,
                row=0
            )
            async def toggle_symbol_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.symbol_check()
                viewself.set_category.symbol_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Collapsed",
                style=active_style if viewself.get_category.collapsed_check() else inactive_style,
                row=0
            )
            async def toggle_collapsed_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.collapsed_check()
                viewself.set_category.collapsed_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Spacehack",
                style=active_style if viewself.get_category.spacehack_check() else inactive_style,
                row=1
            )
            async def toggle_spacehack_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.spacehack_check()
                viewself.set_category.spacehack_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Letter Stitch",
                style=active_style if viewself.get_category.letter_stitch_check() else inactive_style,
                row=1
            )
            async def toggle_letterstitch_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.letter_stitch_check()
                viewself.set_category.letter_stitch_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Reverse",
                style=active_style if viewself.get_category.reverse_check() else inactive_style,
                row=1
            )
            async def toggle_reverse_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.reverse_check()
                viewself.set_category.reverse_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Similarity",
                style=active_style if viewself.get_category.similarity_check() else inactive_style,
                row=2
            )
            async def toggle_similarity_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.similarity_check()
                viewself.set_category.similarity_check(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Syntactic Analysis",
                style=active_style if viewself.get_category.syntactic_analysis() else inactive_style,
                row=2
            )
            async def toggle_syntactic_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.syntactic_analysis()
                viewself.set_category.syntactic_analysis(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

        return Menu_Init()