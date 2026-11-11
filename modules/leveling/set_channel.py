from library.database.guilds import dbguild, server_logs
from library.permissions import prechecks
from modules.leveling.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="leaderboard",
    description="Get the top 10 chatters of the server!"
):

    channel = lightbulb.channel("channel", "Where do we send level-up notifications?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("leveling-set-channel", ctx, permission=[hikari.Permissions.MANAGE_GUILD])

        guild = dbguild(ctx.guild_id)
        success = guild.leveling.set_dedicated_channel(self.channel.id)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Success",
                    description="We'll now send level-up alerts to that channel.",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Error!",
                    description="We couldn't set it to send level-up alerts to that channel.",
                    colour=0xff0000
                )
            )

        await server_logs(ctx.guild_id).create_entry(
            hikari.Embed(
                title="Leveling config changed",
                description=f"{ctx.user.mention} Has just changed the leveling config to send all level-up notifications to {self.channel.mention}."
            )
        )