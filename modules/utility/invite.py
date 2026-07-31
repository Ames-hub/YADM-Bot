from library import datastore as ds
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

@loader.command
class command(
    lightbulb.SlashCommand,
    name="invite",
    description="Want Nodeus on your own server? Run this command!"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        embed = (
            hikari.Embed(
                title=f"Welcome aboard!",
                description=(
                    f"Click this link to invite the bot to your server!",
                    "https://discord.com/oauth2/authorize?client_id=1461801438446616618",
                ),
                colour=0x00ff00
            )
        )

        await ctx.respond(embed)
        