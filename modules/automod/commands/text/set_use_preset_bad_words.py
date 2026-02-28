from modules.automod.commands.text.subgroup import text_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="presetlist",
    description="Toggle whether or not we use the preset banned words list in this server"
):
    
    use_list = lightbulb.boolean("use_list", "Do we use the preset banned words list?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        guild = dbguild(ctx.guild_id)
        success = guild.set.use_preset_word_ban_list(self.use_list)
        if success:
            if self.use_list:
                await ctx.respond(
                    hikari.Embed(
                        title="Using preset banned words",
                        description="273 Bad words have been forbidden.",
                        color=0xff0000
                    )
                )
            else:
                await ctx.respond(
                    hikari.Embed(
                        title="Using server's list only",
                        description="Only words in the word list this server created are banned",
                        color=0x0000ff
                    )
                )
        else:
            await ctx.respond(
                hikari.Embed(
                    title="Failure!",
                    description="We couldn't toggle using this list or not for some reason?"
                )
            )