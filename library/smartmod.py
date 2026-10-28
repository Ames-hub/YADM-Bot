from library import benchmark as bm
from library import datastore as ds
import asyncio
import nltk
import re

# For the syntactic analysis check.
with open('library/preset_insulting_words.txt', 'r') as f:
    insulting_words_list = {w.strip() for w in f.read().lower().splitlines() if w.strip()}

TOKEN_PATTERN = re.compile(r'\b\w+\b')
MENTION_PATTERN = re.compile(r'<@!?\d+>')  # Discord user mentions
MENTION_TOKEN = "usermention"  # What a mention becomes so it survives tokenizing
BOUNDARY_PATTERN = re.compile(r'[.!?;\n]+')  # Where one sentence ends and the next begins
BOUNDARY_TOKEN = "sentenceboundary"

try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('averaged_perceptron_tagger_eng')  # Only downloads when it's missing
nltk.pos_tag(["warm", "up"])  # Loads the tagger once at import

class syntax_analysis:
    """
    This is a text moderation tool which can break down a word into its component parts and detect insults based on heuristics.
    It works by:

    1. Breaking down a word into a normalized word: eg, "i'm" to "i am"
    2. Checking if a banned word is in the message being scanned
    3. Determining by pronouns who is being referred to, eg "Omg I'm a dumbass" does not flag, but "You're a dumbass" gets flagged.
    """
    def __init__(self, channel_id:int=None):
        self.insulting_words = insulting_words_list
        self.self_subject = {"i", "me", "myself", "we", "us", "ourselves"}
        self.self_possessive = {"my", "mine", "our", "ours"}
        self.other_subject = {"you", "yourself"}
        self.other_possessive = {"your", "yours"}
        self.third_person_subject = {"he", "she", "they", "him", "her", "them", "guy", "gal", "person"}
        self.third_person_possessive = {"his", "her", "hers", "their", "theirs"}
        self.imperative_start = {"do", "stop", "try", "don't", "never", "avoid"}
        self.linking_verbs = {"is", "are", "was", "were", "be", "being", "been", "look", "looks", "sound", "sounds", "seem", "seems", "act", "acting"}
        self.negations = {"not", "never", "isnt", "aint"}
        self.insult_window = 6  # Safety cap on how many words past the verb or target to check
        self.modifier_tags = {"DT", "PDT", "PRP$", "RB", "RBR", "RBS", "JJ", "JJR", "JJS", "CC"}  # Tags allowed between the verb and the insult
        self.stoppers = self.negations | {BOUNDARY_TOKEN}  # Ends the walk for an insult word
        self.hedge_words = self.negations | {"if", "whether", "unless"}
        self.hedge_window = 2  # How many words before the target to look for one
        self.intensifiers = {"fucking", "fuckin", "freaking", "friggin", "frickin", "effing", "damn", "damned", "goddamn", "bloody"}  # Trim to match your word list
        self.name_blockers = {"the", "a", "an", "this", "that", "these", "those"} | self.self_possessive | self.other_possessive | self.third_person_possessive

        # Display names (strings) of users who've talked in the last 120 seconds.
        # Treated like proper nouns, so "jack is stupid" can be flagged.
        self.users_talking = ds.d["channel_users_talking"].get(channel_id) or []
        self.name_set, self.max_name_tokens = self.build_name_set(self.users_talking)

    def decontract_text(self, text: str) -> str:
        """
        Expands sentences like "we're" to "we are"
        """
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
        pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in contractions) + r')\b')
        text = pattern.sub(lambda m: contractions[m.group(0)], text)
        return text

    @staticmethod
    def normalize_name(text: str) -> str:
        """
        Lowercases and strips everything except letters and digits: "xX_Jack_Xx" becomes "xxjackxx".
        """
        return re.sub(r'[\W_]+', '', text.lower())

    def build_name_set(self, names: list):
        """
        Returns (set of normalized names, the most words any single name spans).
        """
        name_set = set()
        max_tokens = 1
        for name in names:
            normalized = self.normalize_name(name)
            if len(normalized) < 2:
                continue  # Emoji-only or one-letter names would match everything
            name_set.add(normalized)
            max_tokens = max(max_tokens, len(TOKEN_PATTERN.findall(name)))
        return name_set, max_tokens

    def tokenize(self, text: str):
        """
        Converts a sentence from a sentence of words to a list (basically)
        """
        return TOKEN_PATTERN.findall(text)

    async def tag_tokens(self, tokens: list):
        """
        Synchronous NLTK tagging. Returns a list of (word, Penn Treebank tag).
        """
        def tag_tokens(tokens: list):
            return nltk.pos_tag(tokens)
        return await asyncio.to_thread(tag_tokens, tokens)

    def is_insult(self, word: str) -> bool:
        """
        Checks the insult list, also catching plural/verb forms: "idiots", "sucks".
        """
        if word in self.insulting_words:
            return True
        if word.endswith("es") and word[:-2] in self.insulting_words:
            return True
        return word.endswith("s") and word[:-1] in self.insulting_words

    def match_target(self, words: list, i: int) -> int:
        """
        Returns how many tokens a target starting at index i spans, or 0 if there's none.
        Targets: "you", an @mention, or a display name from users_talking.
        """
        if words[i] in self.other_subject or words[i] == MENTION_TOKEN:
            return 1

        if i > 0 and words[i - 1] in self.name_blockers:
            return 0  # "the cat is stupid" / "my cat is stupid" isn't about a user named Cat

        # Longest names first, so "jack smith" is tried before "jack"
        for length in range(min(self.max_name_tokens, len(words) - i), 0, -1):
            joined = self.normalize_name("".join(words[i:i + length]))
            if joined in self.name_set:
                return length
        return 0

    def find_linked_insult(self, words: list, tags: list, start: int):
        """
        Walks forward from just after a linking verb, skipping modifiers
        (determiners, adverbs, adjectives, conjunctions) until it finds an insult
        or hits something else, like a non-insult noun, a verb, or a negation.
        """
        for k in range(start, min(start + self.insult_window, len(words))):
            if words[k] in self.stoppers:
                return None
            if words[k] in self.intensifiers:
                continue  # "you are fucking awesome" isn't an insult, but "you are a fucking idiot" still hits on "idiot"
            if self.is_insult(words[k]):
                return words[k]
            if tags[k] not in self.modifier_tags:
                return None
        return None

    def find_verb_insult(self, words: list, tags: list, start: int):
        """
        Catches "you suck" / "jack really stinks": an insult word tagged as a verb,
        optionally after adverbs.
        """
        for k in range(start, min(start + self.insult_window, len(words))):
            if words[k] in self.stoppers:
                return None
            if words[k] in self.intensifiers:
                continue  # Swearing as emphasis, not the insult itself
            if tags[k].startswith("RB"):
                continue
            if tags[k].startswith("VB") and self.is_insult(words[k]):
                return words[k]
            return None
        return None

    def is_hedged(self, words: list, i: int) -> bool:
        """
        True when a negation or "if" sits just before the target, within the same sentence:
        "I'm not saying you are stupid", "what if you are an idiot".
        """
        for k in range(i - 1, max(i - 1 - self.hedge_window, -1), -1):
            if words[k] == BOUNDARY_TOKEN:
                return False
            if words[k] in self.hedge_words:
                return True
        return False

    def determine_insult(self, text_grammar: list):
        """
        Flags an insult aimed at "you", an @mention, or a user who's talking:
          - Linking verb: "you are such a complete idiot", "jack is stupid"
          - Verb insult:  "you suck", "jack really stinks"
        Returns (flagged, matched_word).
        """
        words = [word.lower() for word, tag in text_grammar]
        tags = [tag for word, tag in text_grammar]

        for i in range(len(words)):
            span = self.match_target(words, i)
            if not span:
                continue

            if self.is_hedged(words, i):
                continue  # "I'm not saying you are stupid", "what if you are an idiot"

            j = i + span  # First token after the target
            if j >= len(words):
                continue

            if words[j] in self.linking_verbs:
                hit = self.find_linked_insult(words, tags, j + 1)
            else:
                hit = self.find_verb_insult(words, tags, j)

            if hit:
                return True, hit

        return False, None

    async def main(self, text: str):
        bm.benchmark("Insult detection started.")
        text = MENTION_PATTERN.sub(f" {MENTION_TOKEN} ", text)  # "<@123>" becomes "usermention"
        text = BOUNDARY_PATTERN.sub(f" {BOUNDARY_TOKEN} ", text)  # "love you. sucks that you left" shouldn't read as "you sucks"
        text_norm = self.decontract_text(text)
        bm.benchmark("Possible insult message normalised.")

        tokens = self.tokenize(text_norm)
        bm.benchmark("Possible insult message tokenised.")

        grammar = await self.tag_tokens(tokens)
        bm.benchmark("Message grammar determined.")

        guilty = self.determine_insult(grammar)

        return guilty