from unittest.mock import MagicMock
import pytest
from library import automod


# ---------------------------
# Fixtures
# ---------------------------

@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.wordlist.get_list.return_value = ["custombad"]
    guild.get.get_text_filter_level.return_value = 2
    guild.get.do_delete_msg.return_value = False
    guild.get.do_warn_member.return_value = False
    guild.get.do_mute_member.return_value = False
    guild.get.do_kick_member.return_value = False
    guild.get.do_ban_member.return_value = False
    return guild


@pytest.fixture
def mock_dbguild(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(automod, "dbguild", mock)
    return mock


# ---------------------------
# Bad Word List
# ---------------------------

def test_get_bad_word_list_includes_custom(mock_dbguild):
    mock_dbguild.return_value.wordlist.get_list.return_value = ["custombad"]
    mock_dbguild.return_value.get.use_preset_word_ban_list.return_value = False

    result = automod.get_bad_word_list(guild_id=123)
    assert "custombad" in result


# ---------------------------
# Low Level Heuristics
# ---------------------------

def test_equality_detects_bad_word(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["badword"]
    )

    assert automod.checks.heuristics.low.equality("badword") is True
    assert automod.checks.heuristics.low.equality("clean") is False


def test_symbol_check_detects_hidden_word(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["badword"]
    )

    assert automod.checks.heuristics.low.symbol_check("b@a#d$w%o^r&d") is True


def test_symbol_check_leetspeak(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["banned"]
    )

    assert automod.checks.heuristics.low.symbol_check("b@nn3d") is True


def test_collapsed_check_detects_stretched_word(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    assert automod.checks.heuristics.low.collapsed_check("baaaad") is True


# ---------------------------
# Medium Level Heuristics
# ---------------------------

def test_spacehack_detects_combined_words(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["foobar"]
    )

    assert automod.checks.heuristics.medium.spacehack_check("foo bar") is True


def test_letter_stitch_detects_spaced_letters(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    assert automod.checks.heuristics.medium.letter_stitch_check("b a d") is True


def test_reverse_check_detects_reverse(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    assert automod.checks.heuristics.medium.reverse_check("dab") is True


def test_letter_stitch_partial(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    assert automod.checks.heuristics.medium.letter_stitch_check("b a x d") is False
    assert automod.checks.heuristics.medium.letter_stitch_check("b a d") is True


def test_spacehack_edge(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["foobar"]
    )

    assert automod.checks.heuristics.medium.spacehack_check("f o o bar") is False
    assert automod.checks.heuristics.medium.spacehack_check("foo bar") is True


# ---------------------------
# High Level Similarity
# ---------------------------

def test_similarity_check_detects_similar_word(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["banned"]
    )

    result = automod.checks.heuristics.high.similarity_check(
        "bann3d",
        threshold=0.80
    )

    assert result["bad"] is True


# ---------------------------
# High Level - Syntactic Analysis
# ---------------------------

def test_syntactic_allows_self_directed():
    result = automod.checks.heuristics.high.syntactic_analysis(
        "I'm a dumbass"
    )
    assert result["bad"] is False


def test_syntactic_detects_directed_insult():
    result = automod.checks.heuristics.high.syntactic_analysis(
        "You're a dumbass"
    )
    assert result["bad"] is True, f"Got result {result}"


def test_syntactic_probable_case():
    result = automod.checks.heuristics.high.syntactic_analysis(
        "Dumbass."
    )
    assert result["bad"] is True, f"Got result {result}"


# ---------------------------
# Helpers
# ---------------------------

def test_remove_symbols():
    text = "H@e!l#l$o%123"
    cleaned = automod.checks.helpers.remove_symbols(text)
    assert cleaned == "Hello"


def test_collapse_text():
    text = "soooo cooool"
    collapsed = automod.checks.helpers.collapse_text(text)
    assert collapsed == "so col"


def test_reverse_text():
    assert automod.checks.helpers.reverse_text("abc") == "cba"


# ---------------------------
# text_check pipeline
# ---------------------------

def test_text_check_equality_hit(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    result = automod.text_check("bad")
    assert result[0] is True
    assert result[1] == "equality"


def test_text_check_similarity_hit(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["banned"]
    )

    result = automod.text_check("bann3d")
    assert result[0] is True


def test_text_check_clean(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )

    result = automod.text_check("hello world")
    assert result == (False, None), f"Got result {result}"


# ---------------------------
# Duration Formatter
# ---------------------------

def test_convert_duration_txt():
    assert automod.convert_duration_txt(-1) == "Forever"
    assert automod.convert_duration_txt(30) == "30 second(s)"
    assert automod.convert_duration_txt(120) == "2 minute(s)"
    assert automod.convert_duration_txt(7200) == "2 hour(s)"
    assert automod.convert_duration_txt(172800) == "2 day(s)"


# ---------------------------
# AI Vision
# ---------------------------

def test_ai_vision_disabled(monkeypatch):
    monkeypatch.setattr(automod.get, "ai_vision_enabled", lambda: False)

    with pytest.raises(automod.checks.ai_vision.ai_disabled):
        automod.checks.ai_vision.predict_is_nsfw(b"bytes")

# ---------------------------
# generate_hash
# ---------------------------

def test_generate_hash(monkeypatch):
    mock_image = MagicMock()
    mock_image.convert.return_value = mock_image

    monkeypatch.setattr("library.automod.Image.open", lambda _: mock_image)
    monkeypatch.setattr("library.automod.imagehash.phash", lambda img: "hash123")

    result = automod.generate_hash(b"fakebytes")
    assert result == "hash123"