from unittest.mock import MagicMock, patch
import pytest
import hikari

from library.database.welcomer import welcomer

@pytest.fixture
def mock_session():
    with patch("library.database.welcomer.get_session") as mock_get_session:
        session = MagicMock()
        mock_get_session.return_value = session
        yield session

@pytest.fixture
def mock_member():
    member = MagicMock(spec=hikari.Member)
    member.id = 12345
    member.display_name = "TestUser"
    member.username = "testuser"
    member.mention = "@TestUser"
    return member

def test_set_enabled_insert(mock_session):
    mock_session.query().filter().one_or_none.return_value = None
    w = welcomer(1)
    result = w.set_enabled(True)
    
    assert result is True
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

def test_set_enabled_update(mock_session):
    record = MagicMock()
    mock_session.query().filter().one_or_none.return_value = record
    w = welcomer(1)
    result = w.set_enabled(False)

    assert result is True
    assert record.enabled is False
    mock_session.commit.assert_called_once()

def test_is_enabled_true(mock_session):
    record = MagicMock(enabled=True)
    mock_session.query().filter().one_or_none.return_value = record
    w = welcomer(1)

    assert w.is_enabled() is True

def test_is_enabled_false(mock_session):
    mock_session.query().filter().one_or_none.return_value = None
    w = welcomer(1)

    assert w.is_enabled() is False

def test_set_message_insert(mock_session):
    mock_session.query().filter().one_or_none.return_value = None
    w = welcomer(1)
    result = w.set_message("Welcome <username>!")

    assert result is True
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

def test_set_message_update(mock_session):
    record = MagicMock()
    mock_session.query().filter().one_or_none.return_value = record
    w = welcomer(1)
    result = w.set_message("Hello!")

    assert result is True
    assert record.message == "Hello!"
    mock_session.commit.assert_called_once()

def test_get_welcome_msg(mock_session):
    mock_session.query().filter().one_or_none.return_value = "Hello World"
    w = welcomer(1)

    msg = w.get_welcome_msg()
    assert msg == "Hello World"

def test_gen_welcome_msg(mock_session, mock_member):
    w = welcomer(1)
    w.get_welcome_msg = MagicMock(return_value="Hi <display_name>! Your ID is <user_id>.")
    
    message = w.gen_welcome_msg(mock_member)
    assert "<display_name>" not in message
    assert "<user_id>" not in message
    assert "TestUser" in message
    assert str(mock_member.id) in message