from library.database.guilds import dbguild
from library import datastore as ds
from datetime import datetime
from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return
    
    guild = dbguild(event.guild_id)
    if not guild.get.do_filter_spam():
        return

    if event.author.id in ds.d["filter_exemptions"].get(int(event.guild_id), []):
        return

    # Ensure caches exist
    ds.d.setdefault("spam_cache", {})
    ds.d.setdefault("spam_punish_cache", {})
    ds.d["spam_cache"].setdefault(event.guild_id, {})
    ds.d["spam_punish_cache"].setdefault(event.guild_id, {})

    current_time = datetime.now().timestamp()

    last_message_time = ds.d["spam_cache"][event.guild_id].get(event.author.id)
    last_punish_time = ds.d["spam_punish_cache"][event.guild_id].get(event.author.id)

    if last_message_time is not None:
        time_diff = current_time - last_message_time

        if time_diff < 0.6:
            # If they were punished recently, skip (cooldown check only when we have a timestamp)
            if last_punish_time is not None:
                punish_time_diff = current_time - last_punish_time
                if punish_time_diff < 10:
                    return

            # Build the embed
            embed = hikari.Embed(
                title="❄️ Spam detected",
                description=(
                    f"{event.author.mention}, you've been flagged for spamming messages."
                    "\nPlease slow down and avoid sending multiple messages in a short period of time."
                    "\nYou've been placed on a 30 second cooldown."
                ),
            )

            # Record punishment time (only after we decide to punish)
            ds.d["spam_punish_cache"][event.guild_id][event.author.id] = current_time

            # ALSO update last message time
            ds.d["spam_cache"][event.guild_id][event.author.id] = current_time

            await automod.handle_guilty(
                event,
                embed,
                automod.automod_types.SPAM_FILTER,
                whistleblower="Spam Filter"
            )

    # Save last message time (normal case)
    ds.d["spam_cache"][event.guild_id][event.author.id] = current_time