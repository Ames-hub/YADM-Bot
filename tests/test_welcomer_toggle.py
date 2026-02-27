from modules.welcomer.set_enabled import handle_toggle_event
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import hikari



@pytest.mark.asyncio
@patch("modules.welcomer.set_enabled.welcomer")
@patch("modules.welcomer.set_enabled.get")
async def test_handle_toggle_enabled(mock_get, mock_welcomer):
    # Mock bot_name for the embed description
    mock_get.bot_name.return_value = "RailwayBot"

    # Mock welcomer instance
    mock_wc_instance = MagicMock()
    mock_wc_instance.set_enabled.return_value = True
    mock_welcomer.return_value = mock_wc_instance

    # Mock respond function
    mock_respond = AsyncMock()

    # Run function with enabled=True
    await handle_toggle_event(True, guild_id=123, respond_func=mock_respond)

    # It should call set_enabled with True
    mock_wc_instance.set_enabled.assert_called_once_with(True)

    # Respond should be called once
    mock_respond.assert_called_once()
    embed_arg = mock_respond.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "Welcomer Module"
    assert "RailwayBot will now welcome" in embed_arg.description
    assert embed_arg.colour == 0x00ff00


@pytest.mark.asyncio
@patch("modules.welcomer.set_enabled.welcomer")
async def test_handle_toggle_failure(mock_welcomer):
    # Mock welcomer instance fails to toggle
    mock_wc_instance = MagicMock()
    mock_wc_instance.set_enabled.return_value = False
    mock_welcomer.return_value = mock_wc_instance

    mock_respond = AsyncMock()

    # Run function with either True/False, failure should trigger
    await handle_toggle_event(True, guild_id=123, respond_func=mock_respond)

    # It should call set_enabled
    mock_wc_instance.set_enabled.assert_called_once_with(True)

    # Respond should be called with failure embed
    mock_respond.assert_called_once()
    embed_arg = mock_respond.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "Failed!"
    assert "Couldn't toggle" in embed_arg.description
    assert embed_arg.colour == 0xff0000