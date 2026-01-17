import lightbulb
import random
import hikari

loader = lightbulb.Loader()

@loader.command
class command(
    lightbulb.SlashCommand,
    name="rtd",
    description="Roll the dice!"
):

    sides = lightbulb.integer("sides", "How many sides does the dice have?", default=6, min_value=2)
    modifier = lightbulb.integer("modifer", "A modifier to add to the roll.", default=0)
    dice_count = lightbulb.integer("dice_count", "How many dice are there?", default=1, min_value=1)
    force_show_results = lightbulb.boolean("force_results", "Force the bot to show the results of the roll.", default=False)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        # Init value
        roll = 0
        roll_results = []

        # Roll once for each dice
        for _ in range(self.dice_count):
            this_roll = random.randint(1, self.sides)
            roll += this_roll
            roll_results.append(str(this_roll))
        
        # Apply modifier
        roll += self.modifier
        
        if self.dice_count == 1:
            desc = f"The D{self.sides} rolled a **__{roll}__**!"
        else:
            desc = f"You rolled {self.dice_count} D{self.sides} dice and got a **__{roll}__** in total!"
            if self.dice_count <= 10 or self.force_show_results == True:
                desc += f"\n({"+".join(roll_results)})"

        embed = (
            hikari.Embed(
                title="🎲 Roll the dice! 🎲",
                description=desc
            )
        )

        await ctx.respond(embed)
        