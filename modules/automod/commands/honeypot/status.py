from modules.automod.commands.honeypot.subgroup import honeypot_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@honeypot_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="status",
    description="Get the status of the honeypot"
):

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("honeypot status", ctx, hikari.Permissions.MANAGE_MESSAGES)

        guild = dbguild(ctx.guild_id)
        online = guild.honeypot.get_enabled()

        if online:
            await ctx.respond(
                hikari.Embed(
                    title="Honeypot Online",
                    description="The Honeypot is now looking for people to flag."
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Offline",
                    description="The honeypot is not currently online, or is not setup.",
                    colour=0xff0000
                )
            )