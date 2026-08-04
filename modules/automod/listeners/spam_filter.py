from library.database.guilds import dbguild
from library import datastore as ds
from datetime import datetime
from collections import deque
from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

WINDOW_SECONDS = 5

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
    ds.d.setdefault("spam_sustain_cache", {})

    ds.d["spam_cache"].setdefault(event.guild_id, {})
    ds.d["spam_punish_cache"].setdefault(event.guild_id, {})
    ds.d["spam_sustain_cache"].setdefault(event.guild_id, {})

    current_time = datetime.now().timestamp()

    # Rolling message window
    user_window = ds.d["spam_cache"][event.guild_id].setdefault(
        event.author.id,
        deque()
    )

    user_window.append(current_time)

    # Remove old timestamps
    while user_window and current_time - user_window[0] > WINDOW_SECONDS:
        user_window.popleft()

    # Calculate messages per second
    if len(user_window) > 1:
        span = user_window[-1] - user_window[0]
        messages_per_second = (len(user_window) - 1) / max(span, 0.001)
    else:
        messages_per_second = 0.0

    # Track how long they've sustained the threshold
    sustain_start = ds.d["spam_sustain_cache"][event.guild_id].get(event.author.id)

    spam_threshold = guild.get.spam.mps_limit()
    sustain_secs_limit = guild.get.spam.mps_time_limit()

    if messages_per_second >= spam_threshold:
        if sustain_start is None:
            # First time exceeding threshold
            ds.d["spam_sustain_cache"][event.guild_id][event.author.id] = current_time
            return

        sustained_for = current_time - sustain_start

        if sustained_for < sustain_secs_limit:
            return

    else:
        # Rate dropped below threshold, reset sustain timer
        ds.d["spam_sustain_cache"][event.guild_id].pop(event.author.id, None)
        return

    # Punishment cooldown
    last_punish_time = ds.d["spam_punish_cache"][event.guild_id].get(event.author.id)

    if last_punish_time is not None:
        punish_time_diff = current_time - last_punish_time
        if punish_time_diff < 10:
            return

    embed = hikari.Embed(
        title="❄️ Spam detected ❄️",
        description=(
            f"{event.author.mention}, you've been flagged for sustained spamming.\n"
            f"Current rate: **{messages_per_second:.2f} messages/second**\n"
            f"Held for: **{sustained_for:.1f} seconds**\n\n"
            "Please slow down and avoid sending multiple messages in a short period of time.\n"
            "You've been placed on a 30 second cooldown."
        ),
    )

    # Record punishment time
    ds.d["spam_punish_cache"][event.guild_id][event.author.id] = current_time

    # Reset sustain timer after punishment
    ds.d["spam_sustain_cache"][event.guild_id].pop(event.author.id, None)

    await automod.handle_guilty(
        event,
        alert_embed=embed,
        automod_type=automod.automod_types.SPAM_FILTER,
        whistleblower="Spam Filter",
        automod_report={
            "mps": round(messages_per_second, 2),
            "sustained_for": round(sustained_for, 2)
        }
    )