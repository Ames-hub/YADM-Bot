from library.automod import automod_types, convert_duration_txt
from library.database.auditing import server_logs
from library.database.guilds import dbguild
import hikari
import miru

class views:
    def __init__(self, guild_id, automod_category:int):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.automod_category = automod_category

        # 🔹 Ensure guild row exists before doing anything else
        if not self.guild.exists_in_db():
            self.guild.create()

        if automod_category == automod_types.TEXT_FILTER:
            self.set_category = self.guild.set.text
            self.get_category = self.guild.get.text
            self.category_text = "text filtering"
        elif automod_category == automod_types.SPAM_FILTER:
            self.set_category = self.guild.set.spam
            self.get_category = self.guild.get.spam
            self.category_text = "spam filtering"
        elif automod_category == automod_types.IMAGE_FILTER:
            self.set_category = self.guild.set.images
            self.get_category = self.guild.get.images
            self.category_text = "image scanning"
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
        self.do_cooldown = self.get_category.do_cooldown()
        self.announce_infraction = self.get_category.do_announce_infraction()
        self.announce_kick = self.get_category.do_announce_kick()
        self.announce_ban = self.get_category.do_announce_ban()
        return True

    def gen_embed(self, no_refresh:bool=False):
        if not no_refresh:
            self.refresh_automod_data()

        if self.mute_duration != -1:  # -1 = Forever
            mute_duration_text = f"⏳ All {self.category_text} auto-mutes last {convert_duration_txt(self.mute_duration)}."
        else:
            mute_duration_text = "⏳ All auto-mutes last until explicitly cancelled by authorities"

        if self.ban_msg_del_length > 0:
            ban_del_duration_text = f"⏳ Bans result in {convert_duration_txt(self.ban_msg_del_length)} worth of messages being deleted."
        else:
            ban_del_duration_text = "⏳ No messages are deleted on a ban."

        if self.ban_duration > 0:
            ban_duration_text = f"⏳ Auto-Bans last {convert_duration_txt(self.ban_duration)}."
        else:
            ban_duration_text = "⏳ Bans are not performed. (0 second bans)"

        if self.automod_category == automod_types.TEXT_FILTER:
            enabled = self.guild.get.do_text_scan()
            if not enabled:
                disabled_warning = " — Module Disabled"
            else:
                disabled_warning = ""

            embed = hikari.Embed(
                title=f"{self.category_text.capitalize()} Automod Config Menu{disabled_warning}",
                description="The below details how we will behave when users violate *text* moderation rules.\n\n",
                color=0x00ffff
            )
        elif self.automod_category == automod_types.SPAM_FILTER:
            enabled = self.guild.get.do_filter_spam()
            if not enabled:
                disabled_warning = " — Module Disabled"
            else:
                disabled_warning = ""

            embed = hikari.Embed(
                title=f"{self.category_text.capitalize()} Automod Config Menu{disabled_warning}",
                description="The below details how we will behave when users violate *spam* moderation rules.\n\n",
                color=0x00ffff
            )
        elif self.automod_category == automod_types.IMAGE_FILTER:
            enabled = self.guild.get.do_image_filtering()
            if not enabled:
                disabled_warning = " — Module Disabled"
            else:
                disabled_warning = ""

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
            name="Cooldowns",
            value="✅ Enabled" if self.do_cooldown else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="Announce violation",
            value="✅ Will announce to users when they violate rules" if self.announce_infraction else "❌ Will not announce to users when they violate rules",
            inline=True
        )
        embed.add_field(
            name="Announce Kick",
            value="✅ Will announce to users when they are kicked" if self.announce_kick else "❌ Will not announce to users when they are kicked",
            inline=True
        )
        embed.add_field(
            name="Announce Ban",
            value="✅ Will announce to users when they are banned" if self.announce_ban else "❌ Will not announce to users when they are banned",
            inline=True
        )
        embed.add_field(
            name="Ban Duration",
            value=ban_duration_text,
            inline=False
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

            @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, row=4)
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
                style=active_style if viewself.get_category.do_delete_msg() else inactive_style,
                row=1
            )
            async def toggle_del_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_delete_msg()
                viewself.set_category.do_delete_msg(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User's messsages will now {'be deleted' if active else 'not be deleted'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Toggle Warnings",
                style=active_style if viewself.get_category.do_warn_member() else inactive_style,
                row=1
            )
            async def toggle_warn_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_warn_member()
                viewself.set_category.do_warn_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User messages will now {'be warned' if active else 'not be warned'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Toggle Muting",
                style=active_style if viewself.get_category.do_mute_member() else inactive_style,
                row=1
            )
            async def toggle_mute_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_mute_member()
                viewself.set_category.do_mute_member(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User's will now {'be muted' if active else 'not be muted'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

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
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User messages will now {'be kicked' if active else 'not be kicked'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

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
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User messages will now {'be banned' if active else 'not be banned'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Toggle Cooldowns",
                style=active_style if viewself.get_category.do_cooldown() else inactive_style,
                row=2
            )
            async def toggle_cooldown_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_cooldown()
                viewself.set_category.do_cooldown(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User messages will now {'be put on cooldown' if active else 'not be put on cooldown'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

            @miru.button(
                label="Toggle Announcements",
                style=active_style if viewself.get_category.do_announce_infraction() else inactive_style,
                row=3
            )
            async def toggle_announce_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_announce_infraction()
                viewself.set_category.do_announce_infraction(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User violations will now {'be announced' if active else 'not be announced'} on {viewself.category_text} infractions."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    ),
                )

            @miru.button(
                label="Toggle Kick Announcements",
                style=active_style if viewself.get_category.do_announce_kick() else inactive_style,
                row=3
            )
            async def toggle_announce_kick_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_announce_kick()
                viewself.set_category.do_announce_kick(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User kicks will now {'be announced' if active else 'not be announced'} on {viewself.category_text} violations."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )
            
            @miru.button(
                label="Toggle Ban Announcements",
                style=active_style if viewself.get_category.do_announce_ban() else inactive_style,
                row=3
            )
            async def toggle_announce_ban_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                active = not viewself.get_category.do_announce_ban()
                viewself.set_category.do_announce_ban(active)
                button.style = active_style if active else inactive_style
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title=f"{viewself.category_text.capitalize()} Setting Changed",
                        description=(
                            f"User bans will now {'be announced' if active else 'not be announced'} on {viewself.category_text} violations."
                        ),
                        colour=0x00FF00 if active else 0xFFA500
                    )
                    .set_footer(
                        f"Changed by {ctx.user.username} ({ctx.user.id})",
                    )
                )

        return Menu_Init()