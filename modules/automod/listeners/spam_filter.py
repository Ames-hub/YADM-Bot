from library.database.guilds import dbguild
from library import datastore as ds
from cachetools import TTLCache
from collections import deque
from library import automod
import lightbulb
import hashlib
import hikari

loader = lightbulb.Loader()

WINDOW_SECONDS = 5
MIN_MESSAGES = 4  # Must be at least 2, or the maths breaks.

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    """
    Checks for sending lots of messages over a short-ish period of time.
    """
    if not event.is_human:
        return

    guild = dbguild(event.guild_id)

    if event.author.id in ds.d["filter_exemptions"].get(int(event.guild_id), []):
        return

    ds.d["spam_cache"].setdefault(event.guild_id, {})
    ds.d["spam_punish_cache"].setdefault(event.guild_id, {})
    ds.d["spam_sustain_cache"].setdefault(event.guild_id, {})

    current_time = event.message.created_at.timestamp()

    # Rolling message window
    user_window = ds.d["spam_cache"][event.guild_id].setdefault(
        event.author.id,
        deque()
    )

    if user_window and current_time < user_window[-1]:
        # Out-of-order event, keep the window sorted
        user_window = deque(sorted([*user_window, current_time]))
        ds.d["spam_cache"][event.guild_id][event.author.id] = user_window
    else:
        user_window.append(current_time)

    # Remove old timestamps
    while user_window and user_window[-1] - user_window[0] > WINDOW_SECONDS:
        user_window.popleft()

    # Calculate messages per second
    if len(user_window) >= MIN_MESSAGES:
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
            sustain_start = current_time
            ds.d["spam_sustain_cache"][event.guild_id][event.author.id] = sustain_start

        sustained_for = max(current_time - sustain_start, 0.0)

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

    if not guild.get.do_filter_spam():  # Ignore spam if its disabled, but still track it (for other modules)
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
        colour=0xff0000
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

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    """
    Checks for sending many repeated messages
    """
    if not event.is_human:
        return

    # Ignore short messages
    if len(event.message.content) < 200:
        return

    msg_hash = hashlib.sha256(event.message.content.encode('utf-8')).hexdigest()
    user_msgs_said = ds.d["spam_msg_repetition"].get(event.author.id)

    if user_msgs_said is None:
        user_msgs_said = TTLCache(maxsize=25, ttl=600)
        ds.d["spam_msg_repetition"][event.author.id] = user_msgs_said

    # Re-insert it each time so the TTL doesn't kill it while they might be spamming. 
    times_said = user_msgs_said.pop(msg_hash, 0) + 1
    user_msgs_said[msg_hash] = times_said

    if times_said > 4:
        current_time = event.message.created_at.timestamp()

        # Record punishment time
        ds.d["spam_punish_cache"][event.guild_id][event.author.id] = current_time

        guild = dbguild(event.guild_id)
        if not guild.get.do_filter_spam():  # Ignore spam if its disabled, but still track it (for other modules)
            return

        embed = hikari.Embed(
            title="❄️ Spam detected ❄️",
            description="You've sent this message a lot recently, be mindful that this is not allowed.",
            colour=0xff0000
        )

        await automod.handle_guilty(
            event,
            alert_embed=embed,
            automod_type=automod.automod_types.SPAM_FILTER,
            whistleblower="Spam Filter",
            automod_report={
                "times_said": times_said,
            }
        )