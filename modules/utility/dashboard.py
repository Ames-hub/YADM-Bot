from library.permissions import prechecks
from library.settings import get
import lightbulb
import logging
import hikari

loader = lightbulb.Loader()
hostname = get.webui_hostname()

if hostname:
    @loader.command
    class command(
        lightbulb.SlashCommand,
        name="dashboard",
        description="View the bot dashboard!"
    ):

        @lightbulb.invoke
        async def invoke(self, ctx: lightbulb.Context) -> None:
            await prechecks("dashboard", ctx)
            await ctx.respond(
                hikari.Embed(
                    title=f"{get.bot_name().capitalize()} Dashboard",
                    description=(
                        f"[Open Bot Dashboard]({hostname})"
                    ),
                    color=0x5865F2
                )
            )
else:
    logging.info("The WebUI Hostname has not been set in settings, disabling /dashboard command. Run 'bot.py --enable-webui-cmds' to fix this.")