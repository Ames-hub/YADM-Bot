from modules.automod.commands.text.subgroup import text_subgroup
from library.permissions import prechecks
from lightbulb import Choice
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="manual",
    description="View information about the checks and details of the text automod system"
):
    
    request = lightbulb.string(
        "document",
        "Which document do you want to see?",
        choices=[
            Choice("General", "general"),
            Choice("What is a 'check'?", "checks"),
            Choice("Equality Check", "equality"),
            Choice("Symbol Check", "symbol"),
            Choice("Collapsed Check", "collapsed"),
            Choice("Spacehack Check", "spacehack"),
            Choice("Letter Stitch Check", "stitch"),
            Choice("Reverse Check", "reverse"),
            Choice("Similarity Check", "similarity"),
            Choice("Syntatic Analysis Check", "syntatic"),
            Choice("False Readings", "false-readings")
        ]
    )

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("prechecks", ctx, hikari.Permissions.ADMINISTRATOR)

        false_readings_txt = (
            "In any anticheat, any chat filter, any scanning program, this fact has always plagued these tools.\n\n"
            "The constant game is being right as many times as possible while being wrong as little as possible. "
            "With this bot, we have safety-rails in place for the automod to reduce the amount of False Positives.\n\n"
            "If you're wondering what a *False Positive* is, a False Positive is a technical term, and is what's used to refer to "
            "an automod falsely or incorrectly marking someone as a rule-breaker, although they've broken no rules. "
            "And the opposite would be a *False Negative*, where someone was a rule-breaker, but was falsely marked as clean by the system.\n\n"
            "That being said, if you notice an error in our automod's decision making process, resulting in a false-positive, or a false-negative, "
            "please do report it to @friendlyfox.exe on Discord. It would help us a lot!"
        )
        
        embeds = {
            "general": hikari.Embed(
                title="📚 Text Automod System Overview",
                description="Welcome to the Text Automod System! Its a system that helps keep your server chat clean and friendly.",
                color=0x3498db
            ).add_field(
                name="How It Works",
                value="The system checks every message against multiple filters, like layers of security. If a message triggers any filter, it gets flagged and appropriate action is taken.",
                inline=False
            ).add_field(
                name="The 3 Check Levels",
                value="🔹 **Low Level** - Simple but reliable (like a basic match check)\n🔹 **Medium Level** - Smarter checks that catch creative attempts\n🔹 **High Level** - Advanced analysis that understands context, or are somewhat unstable in their wide broad-spectrum attempts to catch attempts.",
                inline=False
            ).add_field(
                name="What Happens When Flagged?",
                value="Depending on server settings, the bot can:\n• Delete the message\n• Warn the user\n• Mute them temporarily\n• Kick or ban them\n• Log everything for moderators\n• Give the user a very short mute, which we call a 'cooldown'",
                inline=False
            )
            .set_footer("(If you don't like configuring stuff, run /setup and we'll do it for you!)"),
            
            "checks": hikari.Embed(
                title="What is a 'Check'?",
                description="A 'check' is a word used to refer to a way that a computer can detect misbehavior.",
                color=0x3498db
            ).add_field(
                name="Three Levels",
                value=(
                    "There's three levels for checking, 1 being simplest and 3 being the most complex."
                    "- **Simple checks** = Basic matching, like 'this word is identical to this swear'\n"
                    "- **Medium checks** = More complicated analysis, like 'd@mn' is leetspeek, and translates to 'damn'\n"
                    "- **Complex checks** = Mostly understands context and can make decisions based on that context.\n"
                ),
                inline=False
            ).add_field(
                name="Why Multiple Checks?",
                value="People can be creative when trying to bypass filters. By using multiple checks, we catch everything from obvious swearing to cleverly disguised attempts.",
                inline=False
            )
            .add_field(
                name="False-Positives, False Negatives",
                value=false_readings_txt
            )
            .set_footer(text="Each check builds on the previous one for maximum protection"),

            "false-readings": hikari.Embed(
                title="False Readings",
                description="The below is an excerpt from another section of the manual, describing what false-positives and false-negatives are."
            ).add_field(
                name="False-Positives, False Negatives",
                value=false_readings_txt
            ),
            
            "equality": hikari.Embed(
                title="🔍 Equality Check",
                description="**Level:** Low • **Reliability:** Very High",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="This is the simplest check. It looks for exact matches of banned words in messages.",
                inline=False
            ).add_field(
                name="Example",
                value="If 'foobar' is banned, it catches:\n✅ `You are a foobar`\n❌ `You are a f o o b a r` (spaces break it)",
                inline=False
            )
            .add_field(
                name="Caveat",
                value="While equality check can only catch the most obvious of text rule violations and misses everything else, this check cannot give false-positives."
            ),
            
            "symbol": hikari.Embed(
                title="✨ Symbol Check",
                description="**Level:** Low • **Reliability:** High",
                color=0x3498db
            ).add_field(
                name="What it does",
                value=(
                    "Translates leetspeak words before checking them. "
                    "Catches things like `f00bar` or `b4dword`, but also looks at the message if it had no symbols or numbers at all. "
                    "That catches things like 'foo!bar'"
                ),
                inline=False
            ).add_field(
                name="Example",
                value=(
                    "It sees:\n`b@d w0rd` -> becomes -> `bad word` then checks if 'bad' or 'word' are banned using the equality check.\n",
                    "Also also sees `foo!bar` as `foobar` as it removes symbols and checks once too"
                ),
                inline=False
            ).add_field(
                name="Why it's useful",
                value="People often replace letters with similar-looking symbols (@ for a, 0 for o). This check sees through those tricks.",
                inline=False
            ),
            
            "collapsed": hikari.Embed(
                title="📏 Collapsed Check",
                description="**Level:** Low • **Reliability:** High",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="Finds words where someone repeats letters in a way that hides them, intentional or not, like `sweeeeeeeeeeaaaaar`.",
                inline=False
            ).add_field(
                name="Example",
                value="`fuuuuuuuuuuck` -> collapses to -> `fuck`\nThen checks if that's banned.",
                inline=False
            ),
            
            "spacehack": hikari.Embed(
                title="🕳️ Spacehack Check",
                description="**Level:** Medium • **Reliability:** Good",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="Catches banned words hidden by splitting them between two words with a space.",
                inline=False
            ).add_field(
                name="Example",
                value="If 'badword' is banned, it catches:\n`bad word` -> combines adjacent words -> `badword`\nAnd flags it!",
                inline=False
            ).add_field(
                name="Real World Analogy",
                value="Like noticing that 'cup cake' and 'cupcake' are the same thing. The space doesn't change the meaning!",
                inline=False
            ),
            
            "stitch": hikari.Embed(
                title="🧵 Letter Stitch Check",
                description="**Level:** Medium • **Reliability:** Good",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="Detects banned words where each letter is separated by spaces, like `b a d w o r d`.",
                inline=False
            ).add_field(
                name="Example",
                value="`f u c k` -> stitches letters together -> `fuck` -> flagged!",
                inline=False
            ),
            
            "reverse": hikari.Embed(
                title="↩️ Reverse Check",
                description="**Level:** Medium • **Reliability:** Good",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="Checks if someone wrote a banned word backwards, like `drowdab` instead of `badword`.",
                inline=False
            ).add_field(
                name="Example",
                value="`kcuf` -> reversed -> `fuck` -> flagged!",
                inline=False
            ),
            
            "similarity": hikari.Embed(
                title="📊 Similarity Check",
                description="**Level:** High • **Reliability:** Moderate (but catches clever attempts)",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="Looks for words that are very similar to banned words (90% match or higher). Catches things like `baddword` (extra d) or `badwordd`.",
                inline=False
            ).add_field(
                name="Example",
                value="If 'badword' is banned, it catches:\n• `badword` (exact)\n• `baddword` (one extra letter)\n• `badw0rd` (number substitution)",
                inline=False
            ).add_field(
                name="Important Note",
                value="This check is much more likely to have false positives (flagging innocent words), which is why it's a high-level check that's used carefully. Its advised you use other checks, like the symbol check. Only use this one if you really need thorough moderation.",
                inline=False
            ),
            
            "syntatic": hikari.Embed(
                title="🧠 Syntactic Analysis Check",
                description="**Level:** High • **Reliability:** High; Smart but Complex",
                color=0x3498db
            ).add_field(
                name="What it does",
                value="This is the smartest check! It understands grammar and context to determine if someone is insulting others vs. themselves.",
                inline=False
            ).add_field(
                name="How it works",
                value="1. Normalizes words (i'm -> i am)\n2. Checks for banned words\n3. Looks at pronouns to see WHO is being insulted",
                inline=False
            ).add_field(
                name="Examples",
                value="✅ `Omg I'm an idiot xD` -> ALLOWED (self-directed)\n❌ `Omg you're such an idiot xD` -> FLAGGED (directed at others)",
                inline=False
            ).add_field(
                name="Pronouns It Understands",
                value="**Self:** I, me, my, myself, we, us\n**Others:** you, your, yourself\n**Third person:** he, she, they, him, her, them",
                inline=False
            )
        }
        
        embed = embeds.get(self.request, embeds["general"])
        
        await ctx.respond(
            embed=embed,
            flags=hikari.MessageFlag.EPHEMERAL
        )