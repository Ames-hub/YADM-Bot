from library import datastore as ds
import lightbulb
import datetime
import hikari

loader = lightbulb.Loader()

@loader.command
class command(
    lightbulb.SlashCommand,
    name="uptime",
    description="Check the bot uptime"
):
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        seconds_online = datetime.datetime.now().timestamp() - ds.d["time_at_boot"].timestamp()
        time_online = (seconds_online // 60) // 60  # Convert to hours

        embed = (
            hikari.Embed(
                title=f"Online for {time_online} Hours",
                description=f"I've been online since {ds.d["time_at_boot"].strftime("%d/%m/%Y, %I:%M %P")}"
            )
        )

        await ctx.respond(embed)
        