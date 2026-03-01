from unittest.mock import MagicMock, patch
from library import automod
import pytest


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
    # Make the mock return a real list
    mock_dbguild.return_value.wordlist.get_list.return_value = ["custombad"]

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

    # reverse of "dab" is "bad"
    assert automod.checks.heuristics.medium.reverse_check("dab") is True


# ---------------------------
# High Level Similarity
# ---------------------------

def test_similarity_check_detects_similar_word(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["banned"]
    )

    # slight variation
    result = automod.checks.heuristics.high.similarity_check("bann3d", threshold=0.80)
    assert result['bad'] is True, f"Result is not True!"

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
# generate_hash
# ---------------------------

def test_generate_hash(monkeypatch):
    mock_image = MagicMock()
    mock_image.convert.return_value = mock_image
    monkeypatch.setattr("library.automod.Image.open", lambda _: mock_image)
    monkeypatch.setattr("library.automod.imagehash.phash", lambda img: "hash123")

    result = automod.generate_hash(b"fakebytes")
    assert result == "hash123"

# ---------------------------
# Edge cases for medium heuristics
# ---------------------------

def test_letter_stitch_partial(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["bad"]
    )
    # Only some letters separated, still should detect
    assert automod.checks.heuristics.medium.letter_stitch_check("b a x d") is False
    assert automod.checks.heuristics.medium.letter_stitch_check("b a d") is True

def test_spacehack_edge(monkeypatch):
    monkeypatch.setattr(
        automod,
        "get_bad_word_list",
        lambda guild_id=None: ["foobar"]
    )
    # word split across more than 2? Only adjacent checked
    assert automod.checks.heuristics.medium.spacehack_check("f o o bar") is False
    assert automod.checks.heuristics.medium.spacehack_check("foo bar") is True