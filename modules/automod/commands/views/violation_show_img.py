import hikari
import miru

class views:
    def __init__(self, guild_id, mod_id, embed: hikari.Embed, photo:hikari.File):
        self.guild_id = guild_id
        self.mod_id = mod_id
        self.embed = embed
        self.photo = photo

        self.status_hidden = True

    def init_view(viewself):
        class Menu_Init(miru.View):
            async def on_timeout(self) -> None:
                self.message.components = []

            @miru.button(
                label="Show Image",
                style=hikari.ButtonStyle.SECONDARY,
                emoji="🖼️"
            )
            async def show_img_btn(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.user.id != viewself.mod_id:
                    return
                embed = viewself.embed


                if viewself.status_hidden:
                    embed.set_image(viewself.photo)
                    button.label = "Hide Image"
                else:
                    embed.set_image(None)
                    button.label = "Show Image"

                await ctx.edit_response(embed, components=self, attachment=None)
                viewself.status_hidden = not viewself.status_hidden

        return Menu_Init(timeout=30)