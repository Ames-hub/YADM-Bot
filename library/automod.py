from library.database.guilds import dbguild, violations
from library.database.db_automod import nsfw_scanner
from library import datastore as ds
from difflib import SequenceMatcher
from library.botapp import botapp
from library.settings import get
import imagehash
import datetime
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

def get_bad_word_list(guild_id):
    bad_word_list = preset_bad_words.copy()
    if guild_id:
        guild = dbguild(guild_id)
        custom_bad_words = guild.wordlist.get_list(blacklist_only=True)
        bad_word_list = bad_word_list + custom_bad_words
    return bad_word_list

def check(text, check_layers=2, guild_id=None):
    """
    Puts some text through all checks.
    """

    if guild_id is not None:
        guild = dbguild(guild_id)
        check_layers = guild.get.get_text_filter_level()

    if check_layers >= 1:
        guilty = checks.heuristics.low.equality(text, guild_id=guild_id)
        if guilty:
            return True
        guilty = checks.heuristics.low.symbol_check(text, guild_id=guild_id)
        if guilty:
            return True
        guilty = checks.heuristics.low.collapsed_check(text, guild_id=guild_id)
        if guilty:
            return True

    if check_layers >= 2:
        guilty = checks.heuristics.medium.spacehack_check(text)
        if guilty:
            return True
        guilty = checks.heuristics.medium.letter_stitch_check(text)
        if guilty:
            return True
        guilty = checks.heuristics.medium.reverse_check(text)
        if guilty:
            return True

    if check_layers >= 3:
        pass

    return False

async def handle_guilty(event:hikari.GuildMessageCreateEvent, alert_embed:hikari.Embed, get_msg_id:bool=False, get_case_id:bool=False):
    """
    A Helper function to handle message content infractions.
    
    :param event: The event listener event object.
    :type event: hikari.GuildMessageCreateEvent
    :param alert_embed: The embed to send to alert the user of their infraction
    :type alert_embed: hikari.Embed
    :param get_msg_id: Return the Message ID for the message we respond with
    :type get_msg_id: bool
    """
    # Check lightbulb cache (note: its practically useless since lightbulb's cache never seems to cache anything. Or I'm doing it wrong.)
    guild = dbguild(event.guild_id)
    guild_name = event.get_guild().name
    cache_expire_time = 86400  # 1 day in seconds
    timestamp_now = datetime.datetime.now().timestamp()
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

    violation = "User broke messaging content moderation rules by either swearing, using racial slurs, or anything else that'd fit the category."

    # TODO: Make the public announcement optional
    try:
        msg = await event.message.respond(alert_embed)
    except hikari.ForbiddenError:
        return False

    # Always add the violation for the record.
    case_id = violations.create_member_violation(
        reporter_id=botapp.get_me().id,
        offender_id=event.author.id,
        time=datetime.datetime.now(),
        violation=violation,
        automated=True
    )
    if not case_id:
        return False

    do_del_msg = guild.get.do_delete_msg()
    if do_del_msg:
        await event.message.delete()
    if guild.get.do_warn_member():
        guild.warnings.add_warning(
            reason=violation,
            mod_id=botapp.get_me().id,
            user_id=event.author.id,
            guild_id=event.guild_id
        )
    if guild.get.do_mute_member():
        mute_duration = guild.get.get_mute_duration()
        await guild.muting.mute_member(
            user_id=event.author.id,
            duration_s=mute_duration,
        )
    if guild.get.do_kick_member():
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
            # TODO: Make this send a message to a bot logs channel, not public chat.
            await event.message.respond("Error kicking user from server!")
    if guild.get.do_ban_member():
        try:
            # TODO: Make sending this toggleable
            await event.member.send(
                embed=hikari.Embed(
                    title="Banished",
                    description=f"You've been detected as breaking the rules of {guild_name} and have been banned.\nReason: {violation}"
                )
            )
        except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
            pass

        delete_msg_seconds = guild.get.get_ban_msg_purgetime()

        # TODO: Make this have a configurable auto-unban on a timer.
        try:
            await event.member.ban(delete_message_seconds=delete_msg_seconds, reason=violation)
        except hikari.ForbiddenError:
            # TODO: Make this send a message to a bot logs channel, not public chat.
            try:
                await event.message.respond("Error banning user!")
            except hikari.ForbiddenError:
                return False
            
    # TODO: Make it post a more detailed variant to a logging channel

    if get_msg_id:
        if get_case_id:
            return {'case_id': case_id, 'msg_id': msg.id}
        return msg.id
    else:
        if get_case_id:
            return case_id
        return True

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

            def symbol_check(text:str, guild_id:int=None) -> bool:
                """
                Equality Check, except with all symbols removed.
                """
                text = str(text)
                text = checks.helpers.remove_symbols(text)
                return checks.heuristics.low.equality(text, guild_id=guild_id)
            
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
                for word in text:
                    for bad_word in get_bad_word_list(guild_id):
                        if word[::-1] == bad_word:
                            return True
                return False
        
        class high:
            def reputation_check(text, user_id):
                return False  # TODO: Finish this
            
            def similarity_check(text:str, guild_id:int=None):
                # Determines how similar 2 strings are by importing the SequenceMatcher class from difflib
                for word in text.split(" "):
                    for item in get_bad_word_list(guild_id):
                        similarity = SequenceMatcher(None, a=word, b=item).ratio()
                        if similarity >= 0.80:
                            return True
                return False