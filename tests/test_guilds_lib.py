import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime

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
# Test muting
# ------------------------
@patch("library.database.guilds.botapp")
@patch("library.database.guilds.get_session")
def test_mute_member_creates_record(mock_get_session, mock_botapp, muting_instance, guild_id, user_id):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_record = MagicMock()
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.refresh.return_value = None
    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None

    # patch muted_role to exist
    with patch.object(muting_instance, 'create_muted_role', AsyncMock(return_value=True)):
        with patch("library.database.guilds.dbguild") as mock_dbguild:
            mock_dbguild.return_value.get.muted_role_id = MagicMock(return_value=999)
            mock_botapp.rest.add_role_to_member = AsyncMock()
            case_id = muting_instance.mute_member(user_id, duration_s=10)
            # This is async, so we need to await it
            import asyncio
            result = asyncio.run(case_id)
            assert result is not False
            mock_session.add.assert_called()
            mock_session.commit.assert_called()

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
            automated=True
        )
        assert entry_id == 1
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

# ------------------------
# Test wordlist modifications
# ------------------------
@patch("library.database.guilds.get_session")
def test_add_word_and_remove_word(mock_get_session, wordlist_instance):
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

# ------------------------
# Test automod set/get
# ------------------------
@patch("library.database.guilds.get_session")
def test_automod_set_get(mock_get_session, automod_set_instance, automod_get_instance):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_session.commit.return_value = None
    mock_session.add.return_value = None

    # test set text filter level
    result = automod_set_instance.text.set_text_filter_level(5)
    assert result is True

    # test get_text_filter_level returns default if no record
    mock_session.query.return_value.filter.return_value.one_or_none.return_value = None
    level = automod_get_instance.text.get_filter_level()
    assert level == 1