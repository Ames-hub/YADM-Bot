from library.botapp import miru_client, botapp
from library.database.guilds import dbguild
import hikari
import miru

class views:
    def __init__(self, guild_id):
        self.guild_id = guild_id

        self.guild = dbguild(self.guild_id)
        
    def refresh_automod_data(self):
        self.do_delete_msg = self.guild.get.do_delete_msg()
        self.do_warnings = self.guild.get.do_warn_member()
        self.do_muting = self.guild.get.do_mute_member()
        self.mute_duration = self.guild.get.get_mute_duration()
        self.do_kick_member = self.guild.get.do_kick_member()
        self.do_ban_member = self.guild.get.do_ban_member()
        return True

    def gen_embed(self, no_refresh:bool=False):
        if no_refresh is False:
            self.refresh_automod_data()

        if self.mute_duration != -1:  # -1 = Forever
            mute_duration_text = f"⏳ All auto-mutes last " + str(self.mute_duration) + " seconds"
        else:
            mute_duration_text = "⏳ All auto-mutes last until explicitly cancelled by authorities"

        filter_level = self.guild.get.get_text_filter_level()
        active_modules_text = ""
        if filter_level >= 1 :
            active_modules_text += "Equality checking, Symbol-hider checking, Multi-letter-hiding checking\n"
        if filter_level >= 2:
            active_modules_text += "Space-Hack checking, Letter stitch checking, Inverse-word checking\n"
        if filter_level == 3:
            active_modules_text += "Reputation checking, Similarity checking, "

        embed=(
            hikari.Embed(
                title="Configuration Menu",
                description="The below details how we will behave when users violate text moderation rules.\n\n"
                f"*Current Text Auto-Moderation Level: {filter_level}*\n"
                f"*Run /automod intensity to change the above level*\n\n"
                f"Current active modules: {active_modules_text}"
            )
            .add_field(
                name="Delete messages",
                value="✅ Will delete messages" if self.do_delete_msg else "❌ Will not delete messages",
                inline=True
            )
            .add_field(
                name="Issue Warnings",
                value="✅ Issues warnings to users" if self.do_warnings else "❌ Does not issue warnings",
                inline=True
            )
            .add_field(
                name="Do muting",
                value="✅ Users will be muted" if self.do_muting else "❌ Users wont be muted",
                inline=True
            )
            .add_field(
                name="Mute Duration",
                value=mute_duration_text,
                inline=True
            )
            .add_field(
                name="Do Kick Users",
                value="✅ Will kick users" if self.do_kick_member else "❌ Does not kick users",
                inline=True
            )
            .add_field(
                name="Do Banning",
                value="✅ Will ban users" if self.do_ban_member else "❌ Does not ban users",
                inline=True
            )
        )

        return embed

    # noinspection PyMethodParameters
    def init_view(viewself):
        active_style = hikari.ButtonStyle.PRIMARY
        inactive_style = hikari.ButtonStyle.SECONDARY

        class Menu_Init(miru.View):
            @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await ctx.edit_response(
                    hikari.Embed(
                        title="Exitting menu.",
                        description="Your settings have been saved.",
                    ),
                    components=[]
                )
                self.stop()  # Called to stop the view

            @miru.button(label="Toggle Deleting", style=active_style if viewself.do_delete_msg else inactive_style)
            async def toggle_del_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                # Set to the opposite of self
                active = not viewself.guild.get.do_delete_msg()
                viewself.guild.set.do_delete_msg(active)
                button.style = active_style if active else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(label="Toggle Warnings", style=active_style if viewself.do_warnings else inactive_style)
            async def toggle_warn_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                # Set to the opposite of self
                active = not viewself.guild.get.do_warn_member()
                viewself.guild.set.do_warn_member(active)
                button.style = active_style if active else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(label="Toggle Muting", style=active_style if viewself.do_muting else inactive_style)
            async def toggle_mute_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                # Set to the opposite of self
                active = not viewself.guild.get.do_mute_member()
                viewself.guild.set.do_mute_member(active)
                button.style = active_style if active else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(label="Toggle Kick Users", style=active_style if viewself.do_kick_member else inactive_style, row=2)
            async def toggle_kick_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                # Set to the opposite of self
                active = not viewself.guild.get.do_kick_member()
                viewself.guild.set.do_kick_member(active)
                button.style = active_style if active else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(label="Toggle Ban Users", style=active_style if viewself.do_ban_member else inactive_style, row=2)
            async def toggle_ban_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                # Set to the opposite of self
                active = not viewself.guild.get.do_ban_member()
                viewself.guild.set.do_ban_member(active)
                button.style = active_style if active else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

        return Menu_Init()