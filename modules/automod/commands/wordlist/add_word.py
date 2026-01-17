from modules.automod.commands.wordlist.subgroup import wordlist_subgroup
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@wordlist_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="add",
    description="Add a word as either blacklisted or whitelisted"
):
    
    word = lightbulb.string("word", "The word to add to the list.")
    blacklisted = lightbulb.boolean("blacklisted", "Is this a blacklisted word or a whitelisted word?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.MANAGE_MESSAGES, ctx)

        word = self.word.lower().strip()
        guild = dbguild(ctx.guild_id)

        word_list = guild.wordlist.get_list()
        if word in word_list:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Already there!",
                    description="That word is pre-existing in the list, and must be removed before it can be added or changed."
                )
            )
            return

        success = guild.wordlist.add_word(word, self.blacklisted)

        if success:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Added!",
                    description=f"This word has been {'blacklisted.' if self.blacklisted else 'whitelisted!'}",
                    colour=0x00ff00 if not self.blacklisted else 0xff0000
                )
            )
        else:
            await ctx.respond(
                embed=hikari.Embed(
                    title="Failure!",
                    description="Couldn't add the word to the word list!\nPlease try again or file a bug report."
                )
            )