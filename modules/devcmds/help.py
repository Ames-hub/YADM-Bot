from library.database.leveling import user_activity
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()

commands_list = [
    # Name, description
    [
        "--help",
        "Gives this list of commands.",
    ],
    [
        "--scan-active-now",
        "Checks who's sent more than the threshold of messages in the last 7 days and gives the active role if appropriate."
    ],
    [
        "--scan-activity-perks-now",
        "Checks which activity perks user's are eligable for, and gives them out if they've sent enough messages."
    ],
    [
        "--set-setting <key> <value>",
        "Use this command to set a variable in the bot's settings."
    ],
    [
        "--list-settings",
        "Use this command to list all existing settings for the bot."
    ],
    [
        "--convert-activity-to-exp",
        "Take how many messages each user has sent, and give 5 exp for each message."
    ]
]

@loader.listener(hikari.MessageCreateEvent)
async def botfunction(event: hikari.MessageCreateEvent):
    if not event.author.id == get.primary_maintainer():
        return

    if event.message.content in ["--help", "--cmds", "--commands"]:
        commands_list_text = "Maintainer-only commands are as follows:\n\n"

        # Highlight for readability.
        do_highlight = False
        for name, desc in commands_list:
            if do_highlight:
                commands_list_text += f"**{name}**\n**{desc}**\n"
            else:
                commands_list_text += f"{name}\n{desc}\n"
            do_highlight = not do_highlight  # Flip the bool

        await event.message.respond(
            hikari.Embed(
                title="DEBUG COMMANDS LIST",
                description=commands_list_text,
                colour=0x0000ff
            )
        )
        await user_activity.scan_users_active()