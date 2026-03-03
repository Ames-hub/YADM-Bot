from library.database.guilds import dbguild
from library import datastore as ds
from library import automod
import lightbulb

import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return
    
    if not event.message.content:
        return

    # if the admins have marked them as exempted, don't interact with them
    if event.author.id in ds.d["filter_exemptions"].get(int(event.guild_id), []):
        return

    message = event.message.content.strip().lower()

    result = automod.text_check(message, guild_id=event.guild_id)    
    guilty = result[0]
    whistleblower = result[1]  # Which check tripped the 'alarms'
    flagged_word = result[2]

    if whistleblower == "syntactic":
        flag_type = result[2]
        full_whistleblower = f"{whistleblower} | {flag_type().__str__()}"
    else:
        full_whistleblower = whistleblower

    if guilty:
        guild = dbguild(event.guild_id)

        desc = f"{event.author.mention}, your message was {"deleted as it was " if guild.get.text.do_delete_msg() else ""}found to violate the rules"
        if whistleblower == "syntactic":
            desc += "\nInsults against other members will not be tolerated."
        elif whistleblower in ['reversing', 'stitching', 'spacehack']:
            desc += "\nAttempts to bypass the automoderation are not accepted."
        else:
            desc += "."  # Adds the full stop at the end.

        embed = hikari.Embed(
            title="Automod Action",
            description=desc
        )

        await automod.handle_guilty(
            event,
            alert_embed=embed,
            automod_type=automod.automod_types.TEXT_FILTER,
            whistleblower=full_whistleblower,
            flagged_word=flagged_word  # Text filter only arg
        )
        return True
    return True