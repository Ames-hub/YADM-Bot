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
    name="penalty",
    description="Set the penalty for triggering the honeypot"
):
    
    penalty = lightbulb.string(
        "penalty",
        "What penalty should we apply to users who trip the honeypot?",
        choices=[
            lightbulb.Choice("Ban Them", "ban"),
            lightbulb.Choice("Mute them", "mute"),
        ]
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("honeypot set-penalty", ctx, hikari.Permissions.ADMINISTRATOR)

        do_ban = self.penalty == "ban"

        guild = dbguild(ctx.guild_id)
        success = guild.honeypot.set_do_ban(do_ban)

        if success:
            await ctx.respond(
                hikari.Embed(
                    title="Honeypot Penalty Set",
                    description=(
                        "User's who fall for the honey-pot will now be banned."
                        if do_ban else
                        "User's who fall for the honey-pot will now be permanently muted.\n"
                        "⚠️ Warning: A bot might continue to DM users privately after muting since it won't be banned"

                    ),
                    colour=0xffff00
                )
            )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failed",
                    description="For some reason, we could not set the penalty.",
                    colour=0xff0000
                )
            )