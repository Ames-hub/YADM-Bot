from modules.moderation.mute import handle_mute_user
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import hikari



@pytest.mark.asyncio
@patch("modules.moderation.mute.dbguild")
async def test_mute_user_success(mock_dbguild):
    # Mock guild and its muting object
    mock_guild_instance = MagicMock()
    mock_guild_instance.muting.mute_member = AsyncMock(return_value=True)
    mock_dbguild.return_value = mock_guild_instance

    # Mock responder function
    mock_respond = AsyncMock()

    # Run function
    await handle_mute_user(
        guild_id=123,
        duration_in_seconds=60,
        user_id=987,
        respond_func=mock_respond,
        reason="Test"
    )

    # Ensure mute_member was called
    mock_guild_instance.muting.mute_member.assert_called_once_with(987, "Test", 60, hardmute=False)

    # Ensure respond_func was called with a success embed
    mock_respond.assert_called_once()
    embed_arg = mock_respond.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed), "Embed argument is not an instance of hikari.Embed"
    assert embed_arg.title == "Muted!", "Embed title is not 'Muted!'"
    assert "Member has been muted until" in embed_arg.description, "Embed description does not contain expected text about mute duration"


@pytest.mark.asyncio
@patch("modules.moderation.mute.dbguild")
async def test_mute_user_failure(mock_dbguild):
    # Mock guild and its muting object
    mock_guild_instance = MagicMock()
    mock_guild_instance.muting.mute_member = AsyncMock(return_value=False)
    mock_dbguild.return_value = mock_guild_instance

    # Mock responder function
    mock_respond = AsyncMock()

    # Run function
    await handle_mute_user(
        guild_id=123,
        duration_in_seconds=60,
        user_id=987,
        respond_func=mock_respond,
        reason="Test"
    )

    # Ensure mute_member was called
    mock_guild_instance.muting.mute_member.assert_called_once_with(987, "Test", 60, hardmute=False)

    # Ensure respond_func was called with a failure embed
    mock_respond.assert_called_once()
    embed_arg = mock_respond.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "Error!"
    assert "Couldn't mute this member" in embed_arg.description