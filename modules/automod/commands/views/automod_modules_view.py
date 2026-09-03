from library.database.auditing import server_logs
from library.database.guilds import dbguild
import hikari
import miru

class views:
    def __init__(self, guild_id:int, mod_id:int):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.mod_id = mod_id

    def gen_embed(self):
        do_txt_scan = self.guild.get.do_text_scan()
        do_image_filtering = self.guild.get.do_image_filtering()
        do_filter_spam = self.guild.get.do_filter_spam()

        embed = (
            hikari.Embed(
                title="Configuration Menu",
                description="The below details what modules are active to detect misbehavior.\n",
                color=0x00ffff
            )
            .add_field(
                name="Scan Text",
                value="✅ We will scan text for rule-breaking messages" if do_txt_scan else "❌ We will not look at text",
                inline=True
            )
            .add_field(
                name="Scan Images",
                value="✅ NSFW Content will be scanned for" if do_image_filtering else "❌ We will not scan images for NSFW content",
                inline=True
            )
            .add_field(
                name="Filter Spam",
                value="✅ Spam will be prevented" if do_filter_spam else "❌ Spam will be ignored",
                inline=True
            )
        )

        return embed

    # noinspection PyMethodParameters
    def init_view(viewself):

        active_style = hikari.ButtonStyle.PRIMARY
        inactive_style = hikari.ButtonStyle.SECONDARY

        class Menu_Init(miru.View):
            @miru.button(
                label="Toggle Text Scanner",
                style=active_style if viewself.guild.get.do_text_scan() else inactive_style
            )
            async def toggle_text_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                current = viewself.guild.get.do_text_scan()
                new_state = not current

                viewself.guild.set.do_text_scan(new_state)
                button.style = active_style if new_state else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Automod settings changed",
                        description=f"Text scanning has been turned {"on" if new_state is False else "off"} by {ctx.author.mention}",
                        colour=0xff0000 if new_state else 0x00ff00
                    )
                )

            @miru.button(
                label="Toggle NSFW Scanner",
                style=active_style if viewself.guild.get.do_image_filtering() else inactive_style
            )
            async def toggle_nsfw_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                current = viewself.guild.get.do_image_filtering()
                new_state = not current

                viewself.guild.set.do_image_filtering(new_state)
                button.style = active_style if new_state else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Automod settings changed",
                        description=f"NSFW Image scanning has been turned {"on" if new_state is False else "off"} by {ctx.author.mention}",
                        colour=0xff0000 if new_state else 0x00ff00
                    )
                )

            @miru.button(
                label="Toggle Spam Filter",
                style=active_style if viewself.guild.get.do_filter_spam() else inactive_style,
            )
            async def toggle_spam_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if viewself.mod_id != ctx.user.id:
                    return
                current = viewself.guild.get.do_filter_spam()
                new_state = not current

                viewself.guild.set.do_filter_spam(new_state)
                button.style = active_style if new_state else inactive_style

                await ctx.edit_response(viewself.gen_embed(), components=self)

                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Automod settings changed",
                        description=f"Spam Filtering has been turned {"on" if new_state is False else "off"} by {ctx.author.mention}",
                        colour=0xff0000 if new_state else 0x00ff00
                    )
                )

            async def on_timeout(self) -> None:
                await viewself.ctx.edit_response(
                    viewself.resp,
                    embed=hikari.Embed(
                        title="Menu Exitted",
                        description="This menu has closed itself after being left open for too long."
                    ),
                    components=[]
                )

            @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, row=2)
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

        return Menu_Init(timeout=60)