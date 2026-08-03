from library.permissions import prechecks
from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.command
class command(
    lightbulb.SlashCommand,
    name="echo",
    description="Repeat after you!"
):
    
    statement = lightbulb.string("text", "What to say?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("echo", ctx)
        string = self.statement.strip()

        result = automod.text_check(string)
        bad = result[0]
        if bad:
            await ctx.respond(
                content=string,
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        await ctx.respond(
            content=string,
        )