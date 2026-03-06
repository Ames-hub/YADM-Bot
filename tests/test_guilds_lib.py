from unittest.mock import patch, MagicMock
from library import datastore as ds
import datetime
import pytest

from library.database import guilds

# ------------------------
# Fixtures
# ------------------------
@pytest.fixture
def guild_id():
    return 123456789

@pytest.fixture
def user_id():
    return 987654321

@pytest.fixture
def muting_instance(guild_id):
    return guilds.muting.guilds(guild_id)

@pytest.fixture
def violations_instance():
    return guilds.violations

@pytest.fixture
def wordlist_instance(guild_id):
    return guilds.wordlist_modify(guild_id)

@pytest.fixture
def warnings_instance(guild_id):
    return guilds.guild_warnings(guild_id)

@pytest.fixture
def automod_set_instance(guild_id):
    return guilds.automod_set(guild_id)

@pytest.fixture
def automod_get_instance(guild_id):
    return guilds.automod_get(guild_id)

# ------------------------
# Test violations
# ------------------------
@patch("library.database.guilds.get_session")
def test_create_member_violation(mock_get_session):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_record = MagicMock()
    mock_record.entry_id = 1
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.refresh.return_value = None
    # Patch the member_violations constructor
    with patch("library.database.guilds.member_violations", return_value=mock_record):
        entry_id = guilds.violations.create_member_violation(
            reporter_id=1,
            offender_id=2,
            time=datetime.datetime.now(),
            violation="test",
            automated=True,
            whistleblower="None, test"
        )
        assert entry_id == 1
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

# ------------------------
# Test wordlist modifications
# ------------------------
@patch("library.database.guilds.get_session")
def test_add_word_and_remove_word(mock_get_session, wordlist_instance):
    ds.d["bad_word_list_cache"] = {}

    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_session.commit.return_value = None
    mock_session.add.return_value = None

    result = wordlist_instance.add_word("badword", blacklisted=True)
    assert result is True
    mock_session.add.assert_called()

    # Patch query return for remove_word
    mock_session.query.return_value.filter.return_value.one_or_none.return_value = MagicMock()

    result2 = wordlist_instance.remove_word("badword")
    assert result2 is True
    mock_session.delete.assert_called()

# ------------------------
# Test guild warnings
# ------------------------
def fake_refresh(obj):
    obj.warn_id = 99

@patch("library.database.guilds.get_session")
def test_add_and_revoke_warning(mock_get_session, warnings_instance):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_record = MagicMock()
    mock_record.warn_id = 99
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.refresh.return_value = None
    mock_session.refresh.side_effect = fake_refresh
    mock_session.query.return_value.filter.return_value.one_or_none.return_value = mock_record

    warn_id = warnings_instance.add_warning("reason", 1, 2)
    assert warn_id == 99
    revoked = warnings_instance.revoke_warning(mock_record.warn_id)
    assert revoked is True
    mock_session.delete.assert_called()