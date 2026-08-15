from library.database.manage import guild_text_automod_text_checks
from library.database.guilds import dbguild, violations
from library.database.db_automod import nsfw_scanner
from library.database.auditing import server_logs
from library.settings import get, observe_conf
from library import datastore as ds
from library import benchmark as bm
from difflib import SequenceMatcher
from library.botapp import botapp
from library import mainydb
from enum import Enum
import imagehash
import datetime
import asyncio
import logging
import hikari
import timm
import re
import io

if get.ai_vision_enabled() is True:
    from PIL import Image
    import torch
    
    NSFW_MODEL_NAME = "Marqo/nsfw-image-detection-384"

    nsfw_scan_model = timm.create_model("hf_hub:Marqo/nsfw-image-detection-384", pretrained=True)
    nsfw_scan_model.eval()

    data_config = timm.data.resolve_model_data_config(nsfw_scan_model)
    transforms = timm.data.create_transform(**data_config, is_training=False)

def convert_duration_txt(seconds:int) -> str:
    if seconds == -1:
        return "Forever"
    elif seconds < 60:
        return f"{seconds} second(s)"
    elif seconds < 3600:
        return f"{seconds // 60} minute(s)"
    elif seconds < 86400:
        return f"{seconds // 3600} hour(s)"
    else:
        return f"{seconds // 86400} day(s)"

# The default ones. Users can add their own.
with open('library/less_nsfw_words.txt', 'r') as f:
    less_nsfw_list = f.read().lower().splitlines()
with open('library/nsfw_words.txt', 'r') as f:
    hard_nsfw_list = f.read().lower().splitlines()
with open('library/slurs_list.txt', 'r') as f:
    slurs_list = f.read().lower().splitlines()
with open('library/swears_list.txt', 'r') as f:
    swears_list = f.read().lower().splitlines()

# For the syntactic analysis check.
with open('library/preset_insulting_words.txt', 'r') as f:
    insulting_words_list = f.read().lower().splitlines()

with open("library/preset_word_whitelist.txt", "r") as f:
    PRESET_WORD_WHITELIST = set(f.read().lower().splitlines())

def _bucket_words_by_length(words) -> dict[int, list[str]]:
    """
    Buckets a collection of words by their length, so length-aware checks
    (like similarity_check) can narrow their search space instead of
    scanning every bad word for every word in a message.
    """
    buckets: dict[int, list[str]] = {}
    for word in words:
        buckets.setdefault(len(word), []).append(word)
    return buckets

def get_bad_word_list(guild_id:int):
    """
    Returns (bad_word_set, length_buckets) for a guild, or for the global
    preset lists if guild_id is None.

    Guild results are cached in ds.d["bad_word_list_cache"] by their guild id and
    are only rebuilt when explicitly invalidated. On guild custom wordlist edits
    or on preset-list toggle changes (both in guilds.py). There is no time-based expiry;
    if you add a new way to change a guild's effective bad word list, make sure it
    also busts this cache entry, or checks will keep using stale data.
    """
    if guild_id:
        cached = ds.d["bad_word_list_cache"].get(guild_id, None)
        if cached is not None:
            return cached["list"], cached["buckets"]

        guild = dbguild(guild_id)
        custom_bad_words = guild.wordlist.get_list(blacklist_only=True)

        bad_list = set()

        block_hardnsfw = guild.get.text.use_preset_hardnsfw_list()
        block_lessnsfw = guild.get.text.use_preset_lessnsfw_list()
        block_slurs = guild.get.text.use_preset_slurs_list()
        block_swears = guild.get.text.use_preset_swears_list()

        if custom_bad_words:
            bad_list.update(custom_bad_words)
        if block_swears:
            bad_list.update(swears_list)
        if block_slurs:
            bad_list.update(slurs_list)
        if block_lessnsfw:
            bad_list.update(less_nsfw_list)
        if block_hardnsfw:
            bad_list.update(hard_nsfw_list)

        buckets = _bucket_words_by_length(bad_list)

        ds.d["bad_word_list_cache"][guild_id] = {
            "list": bad_list,
            "buckets": buckets,
        }

        return bad_list, buckets
    else:
        # ALL
        bad_list = set()
        bad_list.update(swears_list)
        bad_list.update(slurs_list)
        bad_list.update(less_nsfw_list)
        bad_list.update(hard_nsfw_list)
        return bad_list, _bucket_words_by_length(bad_list)

def verdict_whitelist_overwrite(verdict: tuple[bool, str, str, dict]) -> bool:
    """Returns True if the verdict should be overridden by the whitelist."""

    details = verdict[3]

    for check_name, data in details.items():
        if data.get("bad"):
            if check_name == "similarity":
                original_word = data.get("flagged_word")
            else:
                original_word = data.get("word")
            return original_word in PRESET_WORD_WHITELIST

    return False

def text_check(text:str, guild_id=None, observing:bool=False):
    """
    Puts some text through any/all checks.
    Returns: (is_bad, check_name, flagged_word)
    returns observation_data at pos. 3 if observing is True.
    """
    if guild_id is None:
        threshold = 0.85
    else:
        guild = dbguild(guild_id)
        threshold = guild.get.text.similarity_threshold()
        guild_whitelist_words = guild.wordlist.get_list(whitelist_only=True)

    bm.benchmark("Beginning to run a check on text.")
    original_text = text.replace("​", "")  # This removes unicode U+200B. The zero-width unicode, used to break some checks.
    lower_text = original_text.lower()

    # If its None, it'll set it as all words. It won't get anyone if they're meant to be just observed.
    bad_word_list, bad_word_buckets = get_bad_word_list(guild_id if not observing else None)

    # TODO: Make this check per-guild preferences.
    allow_self_insult = True

    bm.benchmark("Got bad word list")

    # Define all checks in order
    check_pipeline = [
        ("equality", lambda: checks.heuristics.low.equality(lower_text, bad_word_list)),
        ("symbol", lambda: checks.heuristics.low.symbol_check(lower_text, bad_word_list)),
        ("collapse", lambda: checks.heuristics.low.collapsed_check(lower_text, bad_word_list)),
        ("spacehack", lambda: checks.heuristics.medium.spacehack_check(lower_text, bad_word_list)),
        ("stitching", lambda: checks.heuristics.medium.letter_stitch_check(lower_text, bad_word_list)),
        ("reversing", lambda: checks.heuristics.medium.reverse_check(lower_text, bad_word_list)),
        ("similarity", lambda: checks.heuristics.high.similarity_check(lower_text, bad_word_list, buckets=bad_word_buckets, threshold=threshold)),
        ("syntactic", lambda: checks.heuristics.high.syntactic_analysis(lower_text, allow_self_insult=allow_self_insult)),
    ]

    # If guild exists, respect its config
    if guild_id:
        checks_allowed: guild_text_automod_text_checks = guild.get.text.checks._get_record()

        if checks_allowed is not None:
            enabled_map = {
                "equality": checks_allowed.equality_check,
                "symbol": checks_allowed.symbol_check,
                "collapse": checks_allowed.collapsed_check,
                "spacehack": checks_allowed.spacehack_check,
                "stitching": checks_allowed.letter_stitch_check,
                "reversing": checks_allowed.reverse_check,
                "similarity": checks_allowed.similarity_check,
                "syntactic": checks_allowed.syntactic_analysis,
            }
        else:
            enabled_map = {
                "equality": False,
                "symbol": False,
                "collapse": False,
                "spacehack": False,
                "stitching": False,
                "reversing": False,
                "similarity": False,
                "syntactic": False,
            }
    else:
        # If no guild, everything runs
        enabled_map = {name: True for name, _ in check_pipeline}

    bm.benchmark("Enabled map determined.")

    final_result = None
    observation_data = {}

    # Run checks
    for name, func in check_pipeline:
        if not enabled_map.get(name):
            if observing:
                observation_data[name] = func()  # Run anyways for debug purposes
            continue

        result = func()
        observation_data[name] = result
        verdict = None

        bm.benchmark(f"Check '{name}' has run.")

        if verdict is None:
            if name == "syntactic":
                if result["bad"]:
                    verdict = (True, name, result['type'], result.get("word", "unknown"), observation_data)
            elif name == "similarity":
                if result["bad"]:
                    verdict = (True, name, result.get("word", "unknown"), observation_data)
                    if verdict_whitelist_overwrite(verdict):
                        verdict = None
            else:
                # Handle checks that return a dictionary with 'bad' and 'word' keys
                if isinstance(result, dict) and result.get("bad"):
                    verdict = (True, name, result.get("word", "unknown"), observation_data)
                    if verdict_whitelist_overwrite(verdict):
                        verdict = None
                # Handle boolean returns from older checks
                elif isinstance(result, bool) and result:
                    verdict = (True, name, "unknown", observation_data)
                    if verdict_whitelist_overwrite(verdict):
                        verdict = None

            if guild_id:
                if result['word'] in guild_whitelist_words:
                    verdict = None  # over-ride

        if verdict is not None:
            if final_result is None:
                final_result = verdict
            if not observing:
                return final_result
            # else: observing, so keep looping to populate observation_data

    bm.benchmark("Result determined.")

    if observing:
        result = final_result if final_result is not None else (False, None, None, observation_data)
        return result
    return False, None, None, observation_data

class automod_types:
    TEXT_FILTER = 1
    SPAM_FILTER = 2
    IMAGE_FILTER = 3

_active_punishments = {}

async def handle_guilty(
        event:hikari.GuildMessageCreateEvent,
        alert_embed:hikari.Embed,
        automod_type: int,
        whistleblower:str,
        get_msg_id:bool=False,
        get_case_id:bool=False,
        automod_report:dict=None
    ):
    """
    A Helper function to handle message content infractions.
    This function is strictly for automatic actions.

    :param event: The event listener event object.
    :type event: hikari.GuildMessageCreateEvent
    :param alert_embed: The embed to send to alert the user of their infraction
    :type alert_embed: hikari.Embed
    :param automod_type: Which category triggered the automod? (1 = Text, 2 = spam, 3 = images)
    :type automod_type: int
    :param whistleblower: The check that flagged the automoderation system.
    :type whistleblower: str
    :param get_msg_id: Return the Message ID for the message we respond with
    :type get_msg_id: bool
    :param get_case_id: Return the Case ID for this violation
    :type get_case_id: bool
    """
    if observe_conf.get_enabled():
        observe_only_list = observe_conf.get_list()
        if event.guild_id in observe_only_list:
            logging.info(f"Violation detected in guild {event.guild_id}, but its set to observe-only. Skipping.")
            return True

    bm.benchmark(f"Beginning penalty sequence for user {event.author.id}.")
    user_key = (event.guild_id, event.author.id)

    flagged_word = None
    if automod_type == automod_types.TEXT_FILTER:
        # IF the automod type is text filter, then flagged word MUST be provided.
        flagged_word = automod_report['flagged_word']
        flagged_word = flagged_word.replace("\n", "")

    if user_key not in _active_punishments:
        _active_punishments[user_key] = asyncio.Lock()

    lock = _active_punishments[user_key]

    try:
        async with lock:
            bm.benchmark("Lock established")
            # Check lightbulb cache (note: its practically useless since lightbulb's cache never seems to cache anything. Or I'm doing it wrong.)
            guild = dbguild(event.guild_id)
            guild_name = event.get_guild().name
            cache_expire_time = 86400  # 1 day in seconds
            timestamp_now = datetime.datetime.now().timestamp()
            logs = server_logs(event.guild_id)
            if not guild_name:
                # Check our cache
                cache_obj = ds.d["guild_name_cache"].get(int(event.guild_id), None)
                if cache_obj:
                    if not timestamp_now - cache_obj['time'] >= cache_expire_time:
                        guild_name = cache_obj['name']
            if not guild_name:
                # Get from discord, add to cache.
                discord_guild = await event.app.rest.fetch_guild(int(event.guild_id))
                ds.d["guild_name_cache"][int(event.guild_id)] = {"name": discord_guild.name, "time": timestamp_now}
                guild_name = discord_guild.name

            bm.benchmark("Guild name found")

            esc_window = guild.get.escalation_window()
            current_warnings = len(guild.warnings.get_by_user(event.author.id, escalation_window=esc_window))

            use_escalation = False
            if automod_type == automod_types.TEXT_FILTER:
                cat_check = guild.get.text
                violation = (
                    f"User <@{event.author.id}> ({event.author.username}) broke messaging content moderation rules, which banned the word \"{flagged_word}\"\n\n"
                )
                use_escalation = guild.get.do_escalate()
                extra_info = (
                    f"The word '{automod_report['suspected_word']}' was "
                    f"compared against the word {automod_report['flagged_word']} with the {automod_report['whistleblower']} check, "
                    "and the message was found to be in violation."
                )
            elif automod_type == automod_types.SPAM_FILTER:
                cat_check = guild.get.spam

                violation = (
                    f"User <@{event.author.id}> ({event.author.username}) broke spam moderation rules by sending too many messages in a short period of time."
                )
                extra_info = (
                    f"User was flagged for sending an average of {automod_report['mps']} messages per second, which was sustained for "
                    f"{automod_report['sustained_for']} seconds."
                )
            elif automod_type == automod_types.IMAGE_FILTER:
                cat_check = guild.get.images
                violation = (
                    f"User <@{event.author.id}> ({event.author.username}) sent an image that was flagged as NSFW by the {get.bot_name()} automod system."
                )
                extra_info = (
                    f"An image that {"has been seen before" if automod_report['seen_before'] else "has been newly catalogued"} "
                    f"was detected by the Image-scanner for NSFW Content and flagged with {automod_report['certainty']}% certainty."
                )

            bm.benchmark("Violation message created.")

            if cat_check.do_announce_infraction():
                try:
                    msg = await event.message.respond(alert_embed)
                except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                    return False
            else:
                # Send it privately
                try:
                    msg = await event.author.send(alert_embed)
                except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                    return False

            # Always add the violation for the record.
            case_id = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: violations.create_member_violation(
                    guild_id=event.guild_id,
                    reporter_id=botapp.get_me().id,
                    offender_id=event.author.id,
                    time=datetime.datetime.now(),
                    violation=violation,
                    automated=True,
                    whistleblower=whistleblower,
                    extra_info=extra_info
                )
            )
            bm.benchmark("Member violation created.")
            # IF it so happens that the violation has a problem and doesn't get created, we should just return and not attempt any punishment actions.
            if not case_id:
                logging.error("WARNING: FAILED TO CREATE CASE ID. IMMEDIATE INSPECTION REQUIRED.")
                return False

            do_mute_member = cat_check.do_mute_member()

            # if we're not to mute, put them on cooldown if told to do so. (Cooldown is a short, short mute)
            if cat_check.do_cooldown() and not do_mute_member:
                if use_escalation:
                    cooldown_threshold = cat_check.escalation.cooldown_threshold()
                    if current_warnings == cooldown_threshold:
                        await guild.muting.mute_member(
                            user_id=event.author.id,
                            reason="VIOLATION AUTO COOLDOWN: " + violation,
                            moderator_id=botapp.get_me().id,
                            duration_s=30,  # 30 sec mute for spam. TODO: Make this configurable.
                            is_cooldown=True
                        )
                else:
                    await guild.muting.mute_member(
                        user_id=event.author.id,
                        reason="VIOLATION AUTO COOLDOWN: " + violation,
                        moderator_id=botapp.get_me().id,
                        duration_s=30,  # 30 sec mute for spam. TODO: Make this configurable.
                        is_cooldown=True
                    )

            do_del_msg = cat_check.do_delete_msg()
            if do_del_msg:
                if use_escalation:
                    msg_deletion_threshold = cat_check.escalation.msg_deletion()
                    if current_warnings == msg_deletion_threshold:
                        await event.message.delete()
                else:
                    await event.message.delete()
            if cat_check.do_warn_member():
                guild.warnings.add_warning(
                    reason=violation,
                    mod_id=botapp.get_me().id,
                    user_id=event.author.id,
                )
            if do_mute_member:
                mute_duration = cat_check.get_mute_duration()
                if use_escalation:
                    mute_threshold = cat_check.escalation.mute_threshold()
                    if current_warnings == mute_threshold:
                        await guild.muting.mute_member(
                            user_id=event.author.id,
                            moderator_id=botapp.get_me().id,
                            reason=violation,
                            duration_s=mute_duration,
                        )
                else:
                    await guild.muting.mute_member(
                        user_id=event.author.id,
                        moderator_id=botapp.get_me().id,
                        reason=violation,
                        duration_s=mute_duration,
                    )
            if cat_check.do_kick_member():
                kick_msg = hikari.Embed(
                    title="Kicked",
                    description=f"You've been detected as breaking the rules of {guild_name} and have been kicked.\nReason: {violation}"
                )
                if use_escalation:
                    kick_member_threshold = cat_check.escalation.kick_member()
                if cat_check.do_announce_kick():
                    if use_escalation:
                        if current_warnings == kick_member_threshold:
                            try:
                                msg = await event.member.send(kick_msg)
                            except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
                                pass
                else:
                    try:
                        msg = await event.member.send(kick_msg)
                    except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
                        pass

                try:
                    if use_escalation:
                        if current_warnings == kick_member_threshold:
                            await event.member.kick(reason=violation)
                    else:
                        await event.member.kick(reason=violation)
                except (hikari.ForbiddenError, hikari.UnauthorizedError):
                    await logs.create_entry(
                        hikari.Embed(
                            title="Error Kicking User!",
                            description=f"I couldn't kick {event.author.mention} even though they broke rules!\nViolation: {violation}",
                            colour=0xff0000
                        )
                    )
                    await msg.delete()
                del msg
            if cat_check.do_ban_member():
                delete_msg_seconds = cat_check.get_ban_msg_purgetime()

                announce_ban = cat_check.do_announce_ban()
                try:
                    if use_escalation:
                        if current_warnings == cat_check.escalation.ban_member():
                            await guild.bans.ban_user(
                                infraction_id=case_id,
                                banned_id=event.author.id,
                                moderator_id=botapp.get_me().id,
                                msg_del_duration=delete_msg_seconds,
                                ban_seconds=cat_check.ban_duration(),
                                reason=violation,
                                announce_ban=announce_ban
                            )
                    else:
                        await guild.bans.ban_user(
                            infraction_id=case_id,
                            banned_id=event.author.id,
                            moderator_id=botapp.get_me().id,
                            msg_del_duration=delete_msg_seconds,
                            ban_seconds=cat_check.ban_duration(),
                            reason=violation,
                            announce_ban=announce_ban
                        )
                except hikari.ForbiddenError:
                    await logs.create_entry(
                        hikari.Embed(
                            title="Error Banning User!",
                            description=f"I couldn't ban {event.author.mention} even though they broke rules!\nViolation: {violation}",
                            colour=0xff0000
                        )
                    )

            bm.benchmark("Penalty dispatched to user account.")

            logs_embed = (
                hikari.Embed(
                    title="Rule Violation Detected",
                    description=violation,
                    colour=0xff0000
                )
                .set_author(name=event.author.display_name, icon=event.author.display_avatar_url)
            )
            if automod_type == automod_types.TEXT_FILTER:
                logs_embed.add_field(
                    name="Violating Content",
                    value=f"{event.author.display_name} said:\n\"{event.message.content}\""
                )
            if automod_type == automod_types.SPAM_FILTER:
                logs_embed.add_field(name="❄️ Time-out", value="User has been put in a 30 second time-out for spamming messages.")
            logs_embed.add_field(
                name="Review",
                value=f"To review this incident in more detail, run `/automod violation` using **Case ID {case_id}**"
            )

            await logs.create_entry(logs_embed)

            bm.benchmark("Created logs entry. ")

            if automod_type == automod_types.IMAGE_FILTER:
                mainydb.nsfw_scanner.archive_img(
                    violation_id=case_id,
                    img_bytes=automod_report['img_bytes']
                )

            bm.benchmark("Now returning data, and ending lock.")

            if get_msg_id:
                if get_case_id:
                    return {'case_id': case_id, 'msg_id': msg.id}
                return msg.id
            else:
                if get_case_id:
                    return case_id
                return True
    finally:
        if not lock.locked():
            _active_punishments.pop(user_key, None)

def generate_hash(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return str(imagehash.phash(img))

class checks:
    class helpers:
        @staticmethod
        def remove_symbols(text:str) -> str:
            text = str(text)
            for symbol in [
                "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", ",", "\"", "'", "." ";", ":", "\\", "|", "{", "}",
                "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "?"
                ]:
                text = text.replace(symbol, "")
            return text

        @staticmethod
        def collapse_text(text:str) -> str:
            # replace 2 or more repeated letters with 1
            return re.sub(r'(.)\1+', r'\1', text.lower())

        @staticmethod
        def reverse_text(text:str):
            return text[::-1]

        @staticmethod
        def bucket_by_length(words: set) -> dict[int, list[str]]:
            """
            Buckets a collection of words by their length, so length-aware checks
            (like similarity_check) can narrow their search space instead of
            scanning every bad word for every word in a message.
            """
            buckets: dict[int, list[str]] = {}
            for word in words:
                buckets.setdefault(len(word), []).append(word)
            return buckets

    class syntax_analysis_check:
        """
        This is a text moderation tool which can break down a word into its component parts and detect insults based on heuristics.
        It works by:

        1. Breaking down a word into a normalized word: eg, "i'm" to "i am"
        2. Checking if a banned word is in the message being scanned
        3. Determining by pronouns who is being referred to, eg "Omg I'm a dumbass" does not flag, but "You're a dumbass" gets flagged.
        """
        class verdict(Enum):
            ALLOW_OK = "ALLOW_OK"
            DELETE_BAD = "DELETE_BAD"
            DELETE_PROBABLE = "DELETE_PROBABLE"
            ALLOW_SELF_DIRECTED = "ALLOW_SELF_DIRECTED"

        def __init__(self):
            self.insulting_words = insulting_words_list
            self.self_subject = {"i", "me", "myself", "we", "us", "ourselves"}
            self.self_possessive = {"my", "mine", "our", "ours"}
            self.other_subject = {"you", "yourself"}
            self.other_possessive = {"your", "yours"}
            self.third_person_subject = {"he", "she", "they", "him", "her", "them", "guy", "gal", "person"}
            self.third_person_possessive = {"his", "her", "hers", "their", "theirs"}
            self.imperative_start = {"do", "stop", "try", "don't", "never", "avoid"}
            self.multi_word_patterns = ["acting like", "looks like"]

        def normalize_text(self, text: str) -> str:
            text = text.lower()
            contractions = {
                "you're": "you are",
                "youre": "you are",
                "i'm": "i am",
                "im": "i am",
                "he's": "he is",
                "hes": "he is",
                "she's": "she is",
                "shes": "she is",
                "they're": "they are",
                "we're": "we are",
                "were": "we are",
                "it's": "it is",
                "don't": "do not",
                "dont": "do not",
                "doesn't": "does not",
                "doesnt": "does not",
                "didn't": "did not",
                "didnt": "did not",
                "can't": "cannot",
                "cant": "cannot",
                "u": "you"
            }
            for c, full in contractions.items():
                text = text.replace(c, full)
            return text

        def tokenize(self, text: str):
            return re.findall(r'\b\w+\b', text)

        def find_subject(self, tokens, banned_index):
            window = 5
            start = max(0, banned_index - window)
            context = tokens[start:banned_index]

            # A possessive pronoun directly before the flagged word (e.g. "your dog")
            # marks the flagged word as something owned, not the target of an insult.
            # Drop it and keep scanning further back for an actual subject/object pronoun.
            possessives = self.self_possessive | self.other_possessive | self.third_person_possessive
            if context and context[-1] in possessives:
                context = context[:-1]

            for w in reversed(context):
                if w in self.self_subject or w in self.self_possessive:
                    return "self"
                elif w in self.other_subject or w in self.other_possessive:
                    return "other"
                elif w in self.third_person_subject or w in self.third_person_possessive:
                    return "other"

            if tokens[0] in self.imperative_start:
                return "other"

            return None

        def detect_insult(self, text: str):
            bm.benchmark("Insult detection started.")
            text_norm = self.normalize_text(text)
            bm.benchmark("Possible insult message normalised.")

            for pattern in self.multi_word_patterns:
                if pattern in text_norm:
                    text_norm = text_norm.replace(pattern, pattern.replace(" ", "_"))

            tokens = self.tokenize(text_norm)
            bm.benchmark("Possible insult message tokenised.")

            for i, word in enumerate(tokens):
                check_word = word.replace("_", " ")

                if check_word in self.insulting_words:
                    subject = self.find_subject(tokens, i)
                    bm.benchmark("Determined subject.")

                    # Grab small context window around the flagged word
                    window = 3
                    start = max(0, i - window)
                    end = min(len(tokens), i + window + 1)
                    context_snippet = " ".join(tokens[start:end]).replace("_", " ")

                    result = {
                        "flagged_word": check_word,
                        "context": context_snippet,
                        "original_text": text
                    }

                    if subject == "other":
                        return self.verdict.DELETE_BAD, result
                    elif subject == "self":
                        return self.verdict.ALLOW_SELF_DIRECTED, result
                    else:
                        continue  # Allow it, its inconclusive.

            return self.verdict.ALLOW_OK, None

    class ai_vision:
        """
        Yes, boo AI. I know. But this does have a practical application, and its not bad for the environment since its a small local model opposed to
        open AI's MASSIVE models.
        """
        class ai_disabled(Exception):
            def __init__(self):
                pass
            def __str__(self):
                return "AI Vision has been disabled on this device."

        @staticmethod
        def predict_is_nsfw(
            image_bytes: bytes,
            guild_id:int=None
        ):
            """
            Predict whether an image is NSFW.
            """
            if not get.ai_vision_enabled():
                raise checks.ai_vision.ai_disabled()

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            is_whitelisted = nsfw_scanner.check_whitelisted(generate_hash(image_bytes))
            if is_whitelisted != -1:  # -1 Means no record
                return {"nsfw": not is_whitelisted, "probability": -1}

            # --- Inference ---
            try:
                with torch.no_grad():
                    output = nsfw_scan_model(transforms(img).unsqueeze(0)).softmax(dim=-1).cpu()

                class_names = nsfw_scan_model.pretrained_cfg["label_names"]

                probability = output[0]
                image_class = class_names[output[0].argmax()]
            except Exception as err:
                logging.error(f"NSFW inference failed", exc_info=err)
                return False
            
            is_nsfw = image_class == "NSFW"

            if guild_id:
                guild = dbguild(guild_id)
                probability = round(float(probability[0]), 2)
                threshold = guild.get.nsfw_scan_threshold()

                if not threshold:
                    return {"nsfw": is_nsfw, "probability": probability}

                if not is_nsfw:
                    return {"nsfw": is_nsfw, "probability": probability}
                else:
                    # Lets guilds have some control over the discrim AI's results
                    if probability >= threshold:
                        return {"nsfw": is_nsfw, "probability": probability}
                    else:
                        return {"nsfw": False, "probability": probability}
            else:
                return {"nsfw": is_nsfw, "probability": round(float(probability[0]), 2)}

    class heuristics:
        """
        Use of heuristic methods to determine if a sentence is clean or not 
        """
        class low:
            """
            Low level checks. Not very advanced, but reliable and almost never false-flagging.
            """
            @staticmethod
            def equality(text: str, bad_word_list: set) -> bool:
                """
                Determines if a sentence is dirty/clean via comparing it to a list of words by matching it.
                """
                text = str(text)

                for word in text.split(" "):
                    if word in bad_word_list:
                        return {'bad': True, 'word': word}

                return {'bad': False, 'word': None}

            @staticmethod
            def symbol_check(text: str, bad_word_list:set) -> bool:
                """
                Equality check, except with symbols removed and basic leetspeak normalized.
                """
                text = str(text)

                # Basic leetspeak normalization
                leet_map = str.maketrans({
                    "0": "o",
                    "1": "i",
                    "3": "e",
                    "4": "a",
                    "5": "s",
                    "7": "t",
                    "8": "b",
                    "@": "a",
                    "$": "s",
                    "!": "i",
                    "(": "c",
                    "{": "c",
                    "[": "c"
                })

                translated_text = text.translate(leet_map)

                result = checks.heuristics.low.equality(translated_text, bad_word_list)
                if result['bad']:
                    return result
                
                # Remove symbols and checks again
                no_symb_text = checks.helpers.remove_symbols(text)
                result = checks.heuristics.low.equality(no_symb_text, bad_word_list)
                if result['bad']:
                    return result
                
                return {'bad': False, 'word': None}
            
            @staticmethod
            def collapsed_check(text:str, bad_word_list:set) -> bool:
                """
                Collapsed text check. Takes words like "fuuuuuuuuuuuuuuuuck" and converts it to "fuck" then runs it through the equality check.
                """
                collapsed_text = checks.helpers.collapse_text(text)
                collapsed_text = checks.helpers.remove_symbols(collapsed_text)  # Remove symbols too
                return checks.heuristics.low.equality(collapsed_text, bad_word_list)

        class medium:
            """
            Medium Level Checks. Semi-Advanced, smart or unique. Tend to be reliable, but slightly prone to false flagging in some specific cases.
            """
            @staticmethod
            def spacehack_check(text:str, bad_word_list:set) -> bool:
                """
                Space Hack Check is a check used to detect when someone hides a banned word by adding a space, like "fo obar" instead of "foo bar"
                """
                text = str(text).lower()
                text = checks.helpers.remove_symbols(text)  # Remove symbols
                text_s = text.split(" ")
                count_1 = 0
                count_2 = 1
                for _ in text_s:
                    if count_2 >= len(text_s):
                        return {'bad': False, 'word': None}  # Reached the end with no violations.
                    w1 = text_s[count_1]
                    w2 = text_s[count_2]
                    count_1 += 1
                    count_2 += 1

                    combined = f"{w1}{w2}"

                    if combined in bad_word_list:
                        return {'bad': True, 'word': combined}

                return {'bad': False, 'word': None}

            @staticmethod
            def letter_stitch_check(text: str, bad_word_list:set) -> bool:
                """
                Letter Stitch Check. detects banned words hidden by separating letters with spaces,
                e.g., "f u c k" or "s h i t".
                """
                text = str(text).lower()
                text = checks.helpers.remove_symbols(text)
                letters = text.split()  # split by spaces

                # join consecutive letters and check for banned words
                for start in range(len(letters)):
                    combined = ""
                    for end in range(start, len(letters)):
                        combined += letters[end]
                        if combined in bad_word_list:
                            return {'bad': True, 'word': combined}

                return {'bad': False, 'word': None}

            @staticmethod
            def reverse_check(text:str, bad_word_list:set) -> dict[bool, str]:
                """
                Reverse Check. Reverses text and sees if people tried to hide it that way.
                """
                text = checks.helpers.remove_symbols(text)
                for word in text.split():
                    reversed_word = checks.helpers.reverse_text(word)
                    if reversed_word in bad_word_list:
                        return {'bad': True, 'word': reversed_word}

                return {'bad': False, 'word': None}

        class high:
            @staticmethod
            def similarity_check(text: str, bad_word_list: set, buckets: dict[int, list[str]] = None, threshold: float = 0.85):
                text = checks.helpers.remove_symbols(text)
                if buckets is None:
                    buckets = _bucket_words_by_length(bad_word_list)

                for word in text.split(" "):
                    char_count = len(word)
                    # Only compare against bad words of similar length.
                    # ratios drop off fast once lengths diverge, so this prunes the search space without missing realistic matches. Hopefully.
                    candidates = (
                        buckets.get(char_count - 1, [])
                        + buckets.get(char_count, [])
                        + buckets.get(char_count + 1, [])
                    )

                    for bad_word in candidates:
                        similarity = SequenceMatcher(None, a=word, b=bad_word).ratio()
                        if similarity >= threshold:
                            return {
                                "bad": True,
                                "sim": similarity,
                                "word": bad_word,
                                "flagged_word": word,
                            }
                return {
                    "bad": False,
                    "sim": 0.0,
                    "word": None,
                    "flagged_word": None
                }

            @staticmethod
            def syntactic_analysis(text: str, allow_self_insult:bool=True):
                checker = checks.syntax_analysis_check()
                result = checker.detect_insult(text)
                if allow_self_insult:
                    bad = result[0] not in [checker.verdict.ALLOW_OK, checker.verdict.ALLOW_SELF_DIRECTED]
                else:
                    bad = result[0] != checker.verdict.ALLOW_OK

                return {
                    "bad": bad,
                    "type": result,
                    "word": result[1]['flagged_word'] if bad else None,
                }