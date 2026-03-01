from modules.utility.on_bot_join import handle_botjoin_event
from unittest.mock import AsyncMock, patch
import pytest
import hikari



@pytest.mark.asyncio
@patch("modules.utility.on_bot_join.botapp")
@patch("modules.utility.on_bot_join.get")
async def test_botjoin_sends_message(mock_get, mock_botapp):
    # Mock get.bot_name
    mock_get.bot_name.return_value = "RailwayBot"

    # Mock REST call
    mock_botapp.rest.create_message = AsyncMock()

    # Run function with a valid channel
    await handle_botjoin_event(channel=123)

    # Should call create_message once
    mock_botapp.rest.create_message.assert_called_once()
    args, kwargs = mock_botapp.rest.create_message.call_args

    # Check channel
    assert kwargs["channel"] == 123

    # Check embed content
    embed_arg = kwargs["embed"]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "RailwayBot Has Joined!"
    assert "Hello! Thank you for picking me" in embed_arg.description

@pytest.mark.asyncio
@patch("modules.utility.on_bot_join.botapp")
async def test_botjoin_no_channel(mock_botapp):
    # Mock REST call
    mock_botapp.rest.create_message = AsyncMock()

    # Run function with None channel
    await handle_botjoin_event(channel=None)

    # Should not call create_message
    mock_botapp.rest.create_message.assert_not_called()


@pytest.mark.asyncio
@patch("modules.utility.on_bot_join.botapp")
async def test_botjoin_rest_exception(mock_botapp):
    # Mock REST call to raise ForbiddenError
    mock_botapp.rest.create_message = AsyncMock(side_effect=hikari.ForbiddenError.__new__(hikari.ForbiddenError))

    # Run function with a valid channel — should not raise
    await handle_botjoin_event(channel=123)

    # Should have attempted call once, but exception is caught
    mock_botapp.rest.create_message.assert_called_once()