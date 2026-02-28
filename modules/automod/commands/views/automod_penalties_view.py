from library.database.guilds import dbguild
from library.automod import automod_types
import hikari
import miru

class views:
    def __init__(self, guild_id, automod_category:int):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.automod_category = automod_category

        if automod_category == automod_types.TEXT_FILTER:
            self.set_category = self.guild.set.text
            self.get_category = self.guild.get.text
            self.category_text = "text"
        elif automod_category == automod_types.SPAM_FILTER:
            self.set_category = self.guild.set.spam
            self.get_category = self.guild.get.spam
            self.category_text = "spam"
        elif automod_category == automod_types.IMAGE_FILTER:
            self.set_category = self.guild.set.images
            self.get_category = self.guild.get.images
            self.category_text = "image"
        else:
            raise ValueError("Invalid automoderation category!")

        self.refresh_automod_data()

    def refresh_automod_data(self):
        self.do_delete_msg = self.get_category.do_delete_msg()
        self.do_warnings = self.get_category.do_warn_member()
        self.do_muting = self.get_category.do_mute_member()
        self.mute_duration = self.get_category.get_mute_duration()
        self.do_kick_member = self.get_category.do_kick_member()
        self.do_ban_member = self.get_category.do_ban_member()
        self.ban_msg_del_length = self.get_category.get_ban_msg_purgetime()
        self.ban_duration = self.get_category.ban_duration()
        return True

    def gen_embed(self, no_refresh:bool=False):
        if not no_refresh:
            self.refresh_automod_data()

        if self.mute_duration != -1:  # -1 = Forever
            mute_duration_text = f"⏳ All {self.category_text} auto-mutes last " + str(self.mute_duration // 60) + " minute(s)"
        else:
            mute_duration_text = "⏳ All auto-mutes last until explicitly cancelled by authorities"

        if self.ban_msg_del_length > 0:
            ban_del_duration_text = f"⏳ Bans result in {self.ban_msg_del_length // 60} minute(s) worth of messages being deleted."
        else:
            ban_del_duration_text = "⏳ No messages are deleted on a ban."

        if self.ban_duration > 0:
            ban_duration_text = f"⏳ Auto-Bans last {self.ban_duration // 60} minute(s)."
        else:
            ban_duration_text = "⏳ Bans are not performed. (0 second bans)"

        if self.automod_category == automod_types.TEXT_FILTER:
            disabled = self.guild.get.do_text_scan()
            if disabled:
                disabled_warning = " — Module Disabled"
            else:
                disabled_warning = ""

            embed = hikari.Embed(
                title=f"{self.category_text.capitalize()} Automod Config Menu{disabled_warning}",
                description="The below details how we will behave when users violate *text* moderation rules.\n\n",
                color=0x00ffff
            )
        elif self.automod_category == automod_types.SPAM_FILTER:
            disabled = self.guild.get.do_filter_spam()
            if disabled:
                disabled_warning = " — Module Disabled"

            embed = hikari.Embed(
                title=f"{self.category_text.capitalize()} Automod Config Menu{disabled_warning}",
                description="The below details how we will behave when users violate *spam* moderation rules.\n\n",
                color=0x00ffff
            )
        elif self.automod_category == automod_types.IMAGE_FILTER:
            disabled = self.guild.get.do_image_filtering()
            if disabled:
                disabled_warning = " — Module Disabled"

            embed = hikari.Embed(
                title=f"{self.category_text.capitalize()} Automod Config Menu{disabled_warning}",
                description="The below details how we will behave when users violate *image* moderation rules.\n\n",
                color=0x00ffff
            )
        else:
            raise ValueError("Invalid automod type!")

        embed.add_field(
            name="Delete messages",
            value="✅ Will delete messages" if self.do_delete_msg else "❌ Will not delete messages",
            inline=True
        )
        embed.add_field(
            name="Issue Warnings",
            value="✅ Issues warnings to users" if self.do_warnings else "❌ Does not issue warnings",
            inline=True
        )
        embed.add_field(
            name="Do muting",
            value="✅ Users will be muted" if self.do_muting else "❌ Users wont be muted",
            inline=True
        )
        embed.add_field(
            name="Do Kick Users",
            value="✅ Will kick users" if self.do_kick_member else "❌ Does not kick users",
            inline=True
        )
        embed.add_field(
            name="Do Banning",
            value="✅ Will ban users" if self.do_ban_member else "❌ Does not ban users",
            inline=True
        )
        embed.add_field(
            name="Ban Duration",
            value=ban_duration_text,
            inline=True
        )
        embed.add_field(
            name="Mute Duration",
            value=mute_duration_text,
            inline=False
        )
        embed.add_field(
            name="On-Ban Message Deletion Length",
            value=ban_del_duration_text,
            inline=False
        )

        return embed

    def init_view(viewself):
        viewself.refresh_automod_data()  # Always sync first

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
                self.stop()

            @miru.button(
                label="Toggle Deleting",
                style=active_style if viewself.get_category.do_delete_msg() else inactive_style
            )
            async def toggle_del_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_delete_msg()
                viewself.set_category.do_delete_msg(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Warnings",
                style=active_style if viewself.get_category.do_warn_member() else inactive_style
            )
            async def toggle_warn_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_warn_member()
                viewself.set_category.do_warn_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Muting",
                style=active_style if viewself.get_category.do_mute_member() else inactive_style
            )
            async def toggle_mute_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_mute_member()
                viewself.set_category.do_mute_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Kick Users",
                style=active_style if viewself.get_category.do_kick_member() else inactive_style,
                row=2
            )
            async def toggle_kick_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_kick_member()
                viewself.set_category.do_kick_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

            @miru.button(
                label="Toggle Ban Users",
                style=active_style if viewself.get_category.do_ban_member() else inactive_style,
                row=2
            )
            async def toggle_ban_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_ban_member()
                viewself.set_category.do_ban_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)

        return Menu_Init()