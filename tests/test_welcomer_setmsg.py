from modules.welcomer.set_msg import handle_setmsg_command
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import hikari



@pytest.mark.asyncio
@patch("modules.welcomer.set_msg.welcomer")
async def test_setmsg_success(mock_welcomer):
    # Mock the welcomer instance to succeed
    mock_wc_instance = MagicMock()
    mock_wc_instance.set_message.return_value = True
    mock_welcomer.return_value = mock_wc_instance

    # Mock responder_func
    mock_responder = AsyncMock()

    # Run the function
    await handle_setmsg_command(guild_id=123, new_msg="Hello!", responder_func=mock_responder)

    # set_message should be called
    mock_wc_instance.set_message.assert_called_once_with("Hello!")

    # responder_func should be called once with success embed
    mock_responder.assert_called_once()
    embed_arg = mock_responder.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "Welcomer Message"
    assert embed_arg.description == "The message has been set!"
    assert embed_arg.colour == 0x00ff00


@pytest.mark.asyncio
@patch("modules.welcomer.set_msg.welcomer")
async def test_setmsg_failure(mock_welcomer):
    # Mock the welcomer instance to fail
    mock_wc_instance = MagicMock()
    mock_wc_instance.set_message.return_value = False
    mock_welcomer.return_value = mock_wc_instance

    mock_responder = AsyncMock()

    # Run the function
    await handle_setmsg_command(guild_id=123, new_msg="Hello!", responder_func=mock_responder)

    # set_message should be called
    mock_wc_instance.set_message.assert_called_once_with("Hello!")

    # responder_func should be called once with failure embed
    mock_responder.assert_called_once()
    embed_arg = mock_responder.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert embed_arg.title == "Failed!"
    assert "Couldn't set the message" in embed_arg.description
    assert embed_arg.colour == 0xff0000