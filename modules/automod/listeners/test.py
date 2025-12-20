from library.botapp import client
import lightbulb

@client.register
class HelloWorld(
    lightbulb.SlashCommand,
    name="hello-world",
    description="Makes the bot say hello world"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await ctx.respond("Hello World!")

loader = lightbulb.Loader()