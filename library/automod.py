import re

# The default ones. Users can add their own.
with open('library/preset_bad_words.txt', 'r') as f:
    bw = f.readlines()
preset_bad_words = []
for word in bw:
    preset_bad_words.append(word.replace("\n", ""))

def check(text, guild_id=None):
    """
    Puts some text through all checks.
    """
    lvl_low_enabled = True
    lvl_medium_enabled = True
    lvl_high_enabled = True

    if guild_id is not None:
        # TODO: If Guild ID is not none, Make this fetch the servers preference.
        pass

    if lvl_low_enabled:
        guilty = checks.heuristics.low.equality(text)
        if guilty:
            return True
        guilty = checks.heuristics.low.symbol_check(text)
        if guilty:
            return True
        guilty = checks.heuristics.low.reverse_check(text)
        if guilty:
            return True
        guilty = checks.heuristics.low.collapsed_check(text)
        if guilty:
            return True
        guilty = checks.heuristics.low.letter_stitch_check(text)
        if guilty:
            return True

    if lvl_medium_enabled:
        guilty = checks.heuristics.medium.spacehack_check(text)
        if guilty:
            return True
        
    if lvl_high_enabled:
        pass

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

    class heuristics:
        """
        Use of heuristic methods to determine if a sentence is clean or not 
        """
        class low:
            """
            Low level checks. Not very advanced, but reliable and almost never false-flagging.
            """
            def equality(text:str) -> bool:
                """
                Determines if a sentence is dirty/clean via comparing it to a list of words by matching it.
                """
                text = str(text)
                for bad_word in preset_bad_words:
                    for word in text.split(" "):
                        if bad_word == word:
                            return True
                        else:
                            pass
                return False

            def symbol_check(text:str) -> bool:
                """
                Equality Check, except with all symbols removed.
                """
                text = str(text)
                text = checks.helpers.remove_symbols(text)
                return checks.heuristics.low.equality(text)

            def reverse_check(text:str) -> bool:
                """
                Reverse Check. Reverses text and sees if people tried to hide it that way.
                """
                text = str(text)
                for word in text:
                    for bad_word in preset_bad_words:
                        if word[::-1] == bad_word:
                            return True
                return False
            
            def collapsed_check(text:str) -> bool:
                """
                Collapsed text check. Takes words like "fuuuuuuuuuuuuuuuuck" and converts it to "fuck" then runs it through the equality check.
                """
                collapsed_text = checks.helpers.collapse_text(text)
                return checks.heuristics.low.equality(collapsed_text)

            def letter_stitch_check(text: str) -> bool:
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
                        if combined in preset_bad_words:
                            return True

                return False

        class medium:
            """
            Medium Level Checks. Semi-Advanced, smart or unique. Tend to be reliable, but slightly prone to false flagging in some specific cases.
            """
            def spacehack_check(text:str) -> bool:
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

                    if combined in preset_bad_words:
                        return True

                return False