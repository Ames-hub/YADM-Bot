from library.database.guilds import dbguild
from library.database import observations
from library.settings import observe_conf
from library import datastore as ds
from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_incoming_event(event: hikari.GuildMessageCreateEvent):  # Could also be the edit event
    if not event.is_human:
        return
    
    if not event.message.content:
        return

    # if the admins have marked them as exempted, don't interact with them
    if event.author.id in ds.d["filter_exemptions"].get(int(event.guild_id), []):
        return

    check_do_observe = observe_conf.get_enabled()
    do_observe = False
    if check_do_observe:
        observe_list = observe_conf.get_list()
        if event.guild_id in observe_list:
            do_observe = True

    guild = dbguild(event.guild_id)
    do_text_scan = guild.get.do_text_scan()
    if not do_text_scan:
        if do_observe is False:
            return

    message = event.message.content.strip().lower()

    result = automod.text_check(message, guild_id=event.guild_id, observing=do_observe)
    guilty = result[0]
    whistleblower = result[1]  # Which check tripped the 'alarms'
    flagged_word = result[2]

    if whistleblower == "syntactic":
        flag_type = result[2][0]
        flagged_word = result[3]
        full_whistleblower = f"{whistleblower} | {flag_type.value}"
    else:
        full_whistleblower = whistleblower

    if guilty:
        desc = (
            f"{event.author.mention}, your message was {"deleted as it was " if guild.get.text.do_delete_msg() else ""}"
            "found to violate the rules, please view the rules channel of the server to avoid further incidents."
        )

        if whistleblower == "syntactic":
            suspected_word = result[2]
            desc += "\nInsults against other members will not be tolerated."
        elif whistleblower in ['reversing', 'stitching', 'spacehack']:
            suspected_word = result[2]
            desc += "\nAttempts to bypass the automoderation are not accepted."
        else:
            suspected_word = result[2]
            desc += "."  # Adds the full stop at the end.

        embed = hikari.Embed(
            title="Automod Action",
            description=desc
        )

        if do_text_scan:
            await automod.handle_guilty(
                event,
                alert_embed=embed,
                automod_type=automod.automod_types.TEXT_FILTER,
                whistleblower=full_whistleblower,
                # Text filter only arg. Flagged word = word that is banned, suspected_word = word in users message that tripped the automod.
                automod_report={'guilty': guilty, 'whistleblower': whistleblower, 'flagged_word': flagged_word, 'suspected_word': suspected_word}
            )
        if do_observe:
            observation = result[3]
            observations.add_entry(
                msg_id=event.message.id,
                channel_id=event.channel_id,
                username=event.author.username,
                msg_content=event.message.content,
                bot_response=f"ACTION: \"{flagged_word}\" has been flagged by the {whistleblower} check. | Report: {observation}"
            )
        return True

    if do_observe:
        check_flags = [value[1]['bad'] for value in result[3].items()]
        if any(check_flags):
            whistleblowers = [key for key, value in result[3].items() if value.get('bad')]
            flagged_words = list(set(value.get('word') for key, value in result[3].items() if value.get('bad')))
            resp = f"ACTION: {", ".join(flagged_words)} has been flagged by the {", ".join(whistleblowers)} checks. | Report: {result[3]}"
        else:
            resp = None

        observations.add_entry(
            msg_id=event.message.id,
            channel_id=event.channel_id,
            username=event.author.username,
            msg_content=event.message.content,
            bot_response=resp
        )
    return True

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    await handle_incoming_event(event)

@loader.listener(hikari.events.GuildMessageUpdateEvent)
async def botfunction(event: hikari.GuildMessageUpdateEvent):
    await handle_incoming_event(event)