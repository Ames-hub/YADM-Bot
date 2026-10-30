from library.database.auditing import server_logs
from library.database.guilds import dbguild
from datetime import datetime, timedelta
from library.botapp import miru_client
from library import datastore as ds
import hikari
import miru

class views:
    def __init__(self, author_id:int, guild_id:int, target_user: hikari.Member):
        self.author_id = author_id
        self.guild_id = guild_id
        self.target_user = target_user
        self.guild = dbguild(self.guild_id)

    def gen_embed(self):
        embed = hikari.Embed(
            title="Ban Confirmation",
            description=f"Are you sure you want to *permanently* ban {self.target_user.mention}?",
            colour=0xFFA500
        )
        return embed

    def gen_ban_embed(days:int=None, failed:bool=False):
        if failed:
            return hikari.Embed(
                title="Ban Failed",
                description="We couldn't ban this user for some reason!",
                colour=0xff0000
            )
        
        unban_time = int((datetime.now() + timedelta(days=days)).timestamp())
        if days == -1:
            return hikari.Embed(
                title="User Banned",
                description="This user has been permanently banned from the server!",
                colour=0xff0000
            )
        else:
            return hikari.Embed(
                title="14 Day Ban",
                description=f"This user has been banned from the server, and will only be allowed to rejoin on <t:{unban_time}:F>!",
                colour=0xff0000
            )

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.author.id != viewself.author_id:
                    return
                
                # Returns the user to the original view
                from modules.moderation.views.profile_view import views as origin_view
                view = origin_view(
                    author_id=viewself.author_id,
                    guild_id=ctx.guild_id,
                    target_user=viewself.target_user
                )
                self.stop()
                embed = await view.gen_embed()
                view_menu = view.init_view()

                await ctx.edit_response(
                    embed=embed,
                    components=view_menu.build(),
                    flags=hikari.MessageFlag.EPHEMERAL
                )

                miru_client.start_view(view_menu)
                await view_menu.wait()

            @miru.button(
                label="Permanent Ban",
                style=hikari.ButtonStyle.DANGER,
            )
            async def perm_ban_user(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                class MyModal(miru.Modal, title="Create User Note"):
                    ban_reason = miru.TextInput(
                        label="Ban Reason",
                        placeholder="Why are you banning them?",
                        required=True,
                        max_length=1024,
                        min_length=10,
                        style=hikari.TextInputStyle.PARAGRAPH,
                    )

                    # The callback function is called after the user hits 'Submit'
                    async def callback(self, ctx: miru.ModalContext) -> None:
                        if not ctx.user.id == viewself.author_id:
                            return
                        if ds.d["high_ping"]:
                            # High ping logic
                            await ctx.defer()

                        await ctx.edit_response(viewself.gen_ban_embed(days=-1), components=[])
                        success = viewself.guild.bans.ban_user(
                            banned_id=viewself.target_user.id,
                            moderator_id=viewself.author_id,
                            msg_del_seconds=viewself.guild.get.text.get_ban_msg_purgetime(),
                            reason=self.ban_reason.value.strip()
                        )
                        if not success:
                            await ctx.edit_response(viewself.gen_ban_embed(failed=True))

                modal = MyModal()
                builder = modal.build_response(miru_client)
                await builder.create_modal_response(ctx.interaction)
                miru_client.start_modal(modal)
                self.stop()

            @miru.button(
                label="2 Week Ban",
                style=hikari.ButtonStyle.SECONDARY,
            )
            async def two_week_ban_user(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                class MyModal(miru.Modal, title="Create User Note"):
                    ban_reason = miru.TextInput(
                        label="Ban Reason",
                        placeholder="Why are you banning them?",
                        required=True,
                        max_length=1024,
                        min_length=10,
                        style=hikari.TextInputStyle.PARAGRAPH,
                    )

                    # The callback function is called after the user hits 'Submit'
                    async def callback(self, ctx: miru.ModalContext) -> None:
                        if not ctx.user.id == viewself.author_id:
                            return
                        if ds.d["high_ping"]:
                            # High ping logic
                            await ctx.defer()

                        await ctx.edit_response(viewself.gen_ban_embed(days=14), components=[])
                        success = viewself.guild.bans.ban_user(
                            banned_id=viewself.target_user.id,
                            moderator_id=viewself.author_id,
                            msg_del_seconds=viewself.guild.get.text.get_ban_msg_purgetime(),
                            reason=self.ban_reason.value.strip()
                        )
                        if not success:
                            await ctx.edit_response(viewself.gen_ban_embed(failed=True))
                            
                modal = MyModal()
                builder = modal.build_response(miru_client)
                await builder.create_modal_response(ctx.interaction)
                miru_client.start_modal(modal)
                self.stop()

            @miru.button(
                label="1 Month Ban",
                style=hikari.ButtonStyle.PRIMARY,
            )
            async def one_month_ban_user(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                class MyModal(miru.Modal, title="Create User Note"):
                    ban_reason = miru.TextInput(
                        label="Ban Reason",
                        placeholder="Why are you banning them?",
                        required=True,
                        max_length=1024,
                        min_length=10,
                        style=hikari.TextInputStyle.PARAGRAPH,
                    )

                    # The callback function is called after the user hits 'Submit'
                    async def callback(self, ctx: miru.ModalContext) -> None:
                        if not ctx.user.id == viewself.author_id:
                            return
                        if ds.d["high_ping"]:
                            # High ping logic
                            await ctx.defer()

                        await ctx.edit_response(viewself.gen_ban_embed(days=31), components=[])
                        success = viewself.guild.bans.ban_user(
                            banned_id=viewself.target_user.id,
                            moderator_id=viewself.author_id,
                            msg_del_seconds=viewself.guild.get.text.get_ban_msg_purgetime(),
                            reason=self.ban_reason.value.strip()
                        )
                        if not success:
                            await ctx.edit_response(viewself.gen_ban_embed(failed=True))
                            
                modal = MyModal()
                builder = modal.build_response(miru_client)
                await builder.create_modal_response(ctx.interaction)
                miru_client.start_modal(modal)
                self.stop()

        return Menu_Init()