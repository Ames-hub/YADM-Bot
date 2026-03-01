from library.database.manage import guild_text_automod_text_checks
from library.database.guilds import dbguild, violations
from library.database.db_automod import nsfw_scanner
from library.database.auditing import server_logs
from library import datastore as ds
from difflib import SequenceMatcher
from library.botapp import botapp
from library.settings import get
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

# The default ones. Users can add their own.
with open('library/preset_bad_words.txt', 'r') as f:
    bw = f.readlines()

preset_bad_words = []
for word in bw:
    preset_bad_words.append(word.replace("\n", ""))

with open('library/preset_insulting_words.txt', 'r') as f:
    iw = f.readlines()

insulting_words_list = []
for word in iw:
    insulting_words_list.append(word.replace("\n", ""))

def get_bad_word_list(guild_id):
    if guild_id:
        guild = dbguild(guild_id)
        custom_bad_words = guild.wordlist.get_list(blacklist_only=True)
        if guild.get.use_preset_word_ban_list():
            bad_word_list = preset_bad_words.copy() + custom_bad_words
        else:
            return custom_bad_words
        return bad_word_list
    else:
        return preset_bad_words.copy()

def text_check(text, guild_id=None):
    """
    Puts some text through any/all checks.
    """

    if guild_id is None:
        threshold = 0.80
    else:
        guild = dbguild(guild_id)
        threshold = guild.get.text.similarity_threshold()

    # Define all checks in order
    check_pipeline = [
        ("equality", lambda: checks.heuristics.low.equality(text, guild_id=guild_id)),
        ("symbol", lambda: checks.heuristics.low.symbol_check(text, guild_id=guild_id)),
        ("collapse", lambda: checks.heuristics.low.collapsed_check(text, guild_id=guild_id)),
        ("spacehack", lambda: checks.heuristics.medium.spacehack_check(text)),
        ("stitching", lambda: checks.heuristics.medium.letter_stitch_check(text)),
        ("reversing", lambda: checks.heuristics.medium.reverse_check(text)),
        ("similarity", lambda: checks.heuristics.high.similarity_check(text, guild_id=guild_id, threshold=threshold)),
        ("syntactic", lambda: checks.heuristics.high.syntactic_analysis(text)),
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

    # Run checks
    for name, func in check_pipeline:
        if not enabled_map.get(name):
            continue

        result = func()

        if name == "syntactic":
            if result["bad"]:
                return True, name, result["type"]
            else:
                return False
        elif name == "similarity":
            if result["bad"]:
                similarity = result['sim']
                return True, similarity
            else:
                return False
        else:
            if result:
                return True, name

    return False, None

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
    ):
    """
    A Helper function to handle message content infractions.
    
    :param event: The event listener event object.
    :type event: hikari.GuildMessageCreateEvent
    :param alert_embed: The embed to send to alert the user of their infraction
    :type alert_embed: hikari.Embed
    :param get_msg_id: Return the Message ID for the message we respond with
    :type get_msg_id: bool
    """
    user_key = (event.guild_id, event.author.id)

    if user_key not in _active_punishments:
        _active_punishments[user_key] = asyncio.Lock()

    lock = _active_punishments[user_key]

    try:
        async with lock:
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

            violation = (
                f"User <@{event.author.id}> ({event.author.username}) broke messaging content moderation rules by either swearing, using racial slurs, "
                "or anything else that'd fit the category."
            )

            # TODO: Make the public announcement optional
            try:
                msg = await event.message.respond(alert_embed)
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                return False

            # Always add the violation for the record.
            case_id = violations.create_member_violation(
                reporter_id=botapp.get_me().id,
                offender_id=event.author.id,
                time=datetime.datetime.now(),
                violation=violation,
                automated=True,
                whistleblower=whistleblower
            )
            if not case_id:
                return False

            if automod_type == automod_types.TEXT_FILTER:
                cat_check = guild.get.text
            elif automod_type == automod_types.SPAM_FILTER:
                cat_check = guild.get.spam
            elif automod_type == automod_types.IMAGE_FILTER:
                cat_check = guild.get.images

            do_del_msg = cat_check.do_delete_msg()
            if do_del_msg:
                await event.message.delete()
            if cat_check.do_warn_member():
                guild.warnings.add_warning(
                    reason=violation,
                    mod_id=botapp.get_me().id,
                    user_id=event.author.id,
                    guild_id=event.guild_id
                )
            if cat_check.do_mute_member():
                mute_duration = cat_check.get_mute_duration()
                await guild.muting.mute_member(
                    user_id=event.author.id,
                    duration_s=mute_duration,
                )
            if cat_check.do_kick_member():
                # TODO: Make messaging on kick toggleable.
                try:
                    await event.member.send(
                        embed=hikari.Embed(
                            title="Kicked",
                            description=f"You've been detected as breaking the rules of {guild_name} and have been kicked.\nReason: {violation}"
                        )
                    )
                except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
                    pass

                try:
                    await event.member.kick(reason=violation)
                except (hikari.ForbiddenError, hikari.UnauthorizedError):
                    logs.create_entry(
                        hikari.Embed(
                            title="Error Kicking User!",
                            description=f"I couldn't kick {event.author.mention} even though they broke rules!\nViolation: {violation}"
                        )
                    )
            if cat_check.do_ban_member():
                delete_msg_seconds = cat_check.get_ban_msg_purgetime()

                try:
                    await guild.bans.ban_user(
                        banned_id=event.author.id,
                        moderator_id=botapp.get_me().id,
                        msg_del_duration=delete_msg_seconds,
                        ban_seconds=cat_check.ban_duration(),
                        reason=violation
                    )
                except hikari.ForbiddenError:
                    logs.create_entry(
                        hikari.Embed(
                            title="Error Banning User!",
                            description=f"I couldn't ban {event.author.mention} even though they broke rules!\nViolation: {violation}"
                        )
                    )
                    
            logs.create_entry(
                hikari.Embed(
                    title="Rule Violation Detected",
                    description=violation
                )
                .add_field(
                    name="Violating Content",
                    value=f"{event.author.display_name} said:\n\"{event.message.content}\""
                )
                .set_author(name=event.author.display_name, icon=event.author.display_avatar_url)
            )

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
        def remove_symbols(text:str) -> str:
            text = str(text)
            for symbol in [
                "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", ",", "\"", "'", "." ";", ":", "\\", "|", "{", "}",
                "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"
                ]:
                text = text.replace(symbol, "")
            return text

        def collapse_text(text:str) -> str:
            # replace 2 or more repeated letters with 1
            return re.sub(r'(.)\1+', r'\1', text.lower())

        def reverse_text(text:str):
            return text[::-1]

    class syntax_analysis_check:
        """
        This is a text moderation tool which can break down a word into its component parts and detect insults based on heuristics.
        It works by:

        1. Breaking down a word into a normalized word: eg, "i'm" to "i am"
        2. Checking if a banned word is in the message being scanned
        3. Determining by pronouns who is being referred to, eg "Omg I'm a dumbass" does not flag, but "You're a dumbass" gets flagged.
        """
        class ALLOW_OK(Exception):
            def __init__(self, *args):
                super().__init__(*args)
            def __str__(self):
                return "ALLOW_OK"
        class DELETE_BAD(Exception):
            def __init__(self, *args):
                super().__init__(*args)
            def __str__(self):
                return "DELETE_BAD"
        class DELETE_PROBABLE(Exception):
            def __init__(self, *args):
                super().__init__(*args)
            def __str__(self):
                return "DELETE_PROBABLE"
        class ALLOW_SELF_DIRECTED(Exception):
            def __init__(self, *args):
                super().__init__(*args)
            def __str__(self):
                return "ALLOW_SELF_DIRECTED"

        def __init__(self):
            self.insulting_words = insulting_words_list
            self.self_pronouns = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ourselves"}
            self.other_pronouns = {"you", "your", "yours", "yourself"}
            self.third_person = {"he", "she", "they", "him", "her", "them", "his", "hers", "their", "that", "this", "those", "these", "guy", "gal", "person"}
            self.imperative_start = {"do", "stop", "try", "don't", "never", "avoid"}
            self.multi_word_patterns = ["acting like", "looks like"]

        def normalize_text(self, text: str) -> str:
            text = text.lower()
            contractions = {
                "you're": "you are",
                "i'm": "i am",
                "he's": "he is",
                "she's": "she is",
                "they're": "they are",
                "we're": "we are",
                "it's": "it is",
                "don't": "do not",
                "doesn't": "does not",
                "didn't": "did not",
                "can't": "cannot"
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

            for w in reversed(context):
                if w in self.self_pronouns:
                    return "self"
                elif w in self.other_pronouns:
                    return "other"
                elif w in self.third_person:
                    return "other"

            if tokens[0] in self.imperative_start:
                return "other"

            return None

        def detect_insult(self, text: str) -> str:
            text_norm = self.normalize_text(text)

            for pattern in self.multi_word_patterns:
                if pattern in text_norm:
                    text_norm = text_norm.replace(pattern, pattern.replace(" ", "_"))

            tokens = self.tokenize(text_norm)

            for i, word in enumerate(tokens):
                check_word = word.replace("_", " ")
                if check_word in self.insulting_words:
                    subject = self.find_subject(tokens, i)
                    if subject == "other":
                        return self.DELETE_BAD
                    elif subject == "self":
                        return self.ALLOW_SELF_DIRECTED
                    else:
                        return self.DELETE_PROBABLE

            return self.ALLOW_OK

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
            def equality(text:str, guild_id:int=None) -> bool:
                """
                Determines if a sentence is dirty/clean via comparing it to a list of words by matching it.
                """
                text = str(text)

                bad_word_list = get_bad_word_list(guild_id)

                for bad_word in bad_word_list:
                    for word in text.split(" "):
                        if bad_word == word:
                            return True
                        else:
                            pass
                return False

            def symbol_check(text: str, guild_id: int = None) -> bool:
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

                guilty = checks.heuristics.low.equality(translated_text, guild_id=guild_id)
                if guilty:
                    return True
                
                # Remove symbols and checks again
                no_symb_text = checks.helpers.remove_symbols(text)
                guilty = checks.heuristics.low.equality(no_symb_text, guild_id=guild_id)
                if guilty:
                    return True
            
            def collapsed_check(text:str, guild_id:int=None) -> bool:
                """
                Collapsed text check. Takes words like "fuuuuuuuuuuuuuuuuck" and converts it to "fuck" then runs it through the equality check.
                """
                collapsed_text = checks.helpers.collapse_text(text)
                return checks.heuristics.low.equality(collapsed_text, guild_id=guild_id)

        class medium:
            """
            Medium Level Checks. Semi-Advanced, smart or unique. Tend to be reliable, but slightly prone to false flagging in some specific cases.
            """
            def spacehack_check(text:str, guild_id:int=None) -> bool:
                """
                Space Hack Check is a check used to detect when someone hides a banned word by adding a space, like "fo obar" instead of "foo bar"
                """
                text = str(text).lower()
                text_s = text.split(" ")
                count_1 = 0
                count_2 = 1
                for _ in text_s:
                    if count_2 >= len(text_s):
                        return False  # Reached the end with no violations.
                    w1 = text_s[count_1]
                    w2 = text_s[count_2]
                    count_1 += 1
                    count_2 += 1

                    combined = f"{w1}{w2}"

                    if combined in get_bad_word_list(guild_id):
                        return True

                return False
            
            def letter_stitch_check(text: str, guild_id:int=None) -> bool:
                """
                Letter Stitch Check. detects banned words hidden by separating letters with spaces,
                e.g., "f u c k" or "s h i t".
                """
                text = str(text).lower()
                letters = text.split()  # split by spaces

                # join consecutive letters and check for banned words
                for start in range(len(letters)):
                    combined = ""
                    for end in range(start, len(letters)):
                        combined += letters[end]
                        if combined in get_bad_word_list(guild_id):
                            return True

                return False
            
            def reverse_check(text:str, guild_id:int=None) -> bool:
                """
                Reverse Check. Reverses text and sees if people tried to hide it that way.
                """
                text = str(text)
                for word in text.split():
                    for bad_word in get_bad_word_list(guild_id):
                        if checks.helpers.reverse_text(word) == bad_word:
                            return True
                return False
        
        class high:
            def similarity_check(text:str, guild_id:int=None, threshold:float=0.80):
                # Determines how similar 2 strings are by importing the SequenceMatcher class from difflib
                bad_word_list = get_bad_word_list(guild_id)
                for word in text.split(" "):
                    for item in bad_word_list:
                        similarity = SequenceMatcher(None, a=word, b=item).ratio()
                        if similarity >= threshold:
                            return {
                                "bad": True,
                                "sim": similarity
                            }
                return {
                    "bad": False,
                    "sim": 0.0
                }
            
            def syntactic_analysis(text: str):
                checker = checks.syntax_analysis_check()
                result = checker.detect_insult(text)
                bad = result not in [checker.ALLOW_OK, checker.ALLOW_SELF_DIRECTED]
                return {
                    "bad": bad,
                    "type": result
                }