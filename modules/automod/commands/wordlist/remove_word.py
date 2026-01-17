from modules.automod.commands.wordlist.subgroup import wordlist_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@wordlist_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="remove",
    description="Remove a word that was either blacklisted or whitelisted"
):
    
    word = lightbulb.string("word", "The word to remove from the list.")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_MESSAGES, ctx)

        word = self.word.lower().strip()
        guild = dbguild(ctx.guild_id)

        word_list = guild.wordlist.get_list()
        if word not in word_list:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Not Found!",
                    description="That word is not in the list."
                )
            )
            return

        success = guild.wordlist.remove_word(word)

        if success:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Removed.",
                    description=f"This word has been removed from the list.",
                    colour=0x00ff00
                )
            )
        else:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Failure!",
                    description="Couldn't remove the word from the word list. Please try again or file a bug report."
                )
            )