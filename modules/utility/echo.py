import lightbulb

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
        string = self.statement.strip()

        await ctx.respond(
            content=string,
        )