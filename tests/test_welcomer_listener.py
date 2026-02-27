from modules.welcomer.on_user_join import handle_userjoin_event
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.mark.asyncio
@patch("modules.welcomer.on_user_join.welcomer")
@patch("modules.welcomer.on_user_join.botapp")
async def test_welcome_disabled(mock_botapp, mock_welcomer):
    mock_wc_instance = MagicMock()
    mock_wc_instance.is_enabled.return_value = False
    mock_welcomer.return_value = mock_wc_instance

    mock_botapp.rest.create_message = AsyncMock()

    await handle_userjoin_event(
        guild_id=123,
        user_display_name="Ame",
        system_channel_id=456
    )

    mock_botapp.rest.create_message.assert_not_called()

@pytest.mark.asyncio
@patch("modules.welcomer.on_user_join.welcomer")
@patch("modules.welcomer.on_user_join.botapp")
async def test_welcome_sends_message(mock_botapp, mock_welcomer):
    mock_wc_instance = MagicMock()
    mock_wc_instance.is_enabled.return_value = True
    mock_wc_instance.get_welcome_msg.return_value = "Welcome to the server!"
    mock_welcomer.return_value = mock_wc_instance

    # Mock REST call so discord doesn't hear shit
    mock_botapp.rest.create_message = AsyncMock()

    # Run function
    await handle_userjoin_event(
        guild_id=123,
        user_display_name="Ame",
        system_channel_id=456
    )

    # Assert message was sent
    mock_botapp.rest.create_message.assert_called_once()

    args, kwargs = mock_botapp.rest.create_message.call_args
    assert kwargs["channel"] == 456
    assert kwargs["embed"].title == "Ame Has Joined"
    assert kwargs["embed"].description == "Welcome to the server!"