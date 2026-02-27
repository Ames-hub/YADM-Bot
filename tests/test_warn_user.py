from modules.moderation.warnings.add_warning import handle_warn_user
from unittest.mock import AsyncMock, MagicMock, patch
from library import datastore as ds
import datetime
import pytest
import hikari


@pytest.mark.asyncio
@patch("modules.moderation.warnings.add_warning.dbguild")
@patch("modules.moderation.warnings.add_warning.botapp")
async def test_warn_success(mock_botapp, mock_dbguild):
    # Mock guild + warning creation
    mock_guild_instance = MagicMock()
    mock_guild_instance.warnings.add_warning.return_value = 1
    mock_dbguild.return_value = mock_guild_instance

    # Mock fetch_guild
    mock_botapp.rest.fetch_guild = AsyncMock()
    mock_botapp.rest.fetch_guild.return_value = MagicMock(name="TestGuild")
    mock_botapp.rest.fetch_guild.return_value.name = "TestGuild"

    # Mock user
    mock_user = MagicMock()
    mock_user.id = 999
    mock_user.mention = "@Ame"
    mock_user.send = AsyncMock()

    # Mock responder
    mock_responder = AsyncMock()

    ds.d["guild_name_cache"] = {}

    await handle_warn_user(
        guild_id=123,
        user=mock_user,
        reason="Bad behavior",
        responder_func=mock_responder
    )

    # Warning was added
    mock_guild_instance.warnings.add_warning.assert_called_once_with(
        reason="Bad behavior",
        mod_id=999,
        user_id=999
    )

    # User was DM'd
    mock_user.send.assert_called_once()

    # Confirmation embed sent
    mock_responder.assert_called_once()


@pytest.mark.asyncio
@patch("modules.moderation.warnings.add_warning.dbguild")
@patch("modules.moderation.warnings.add_warning.botapp")
async def test_warn_dm_fails(mock_botapp, mock_dbguild):
    mock_guild_instance = MagicMock()
    mock_guild_instance.warnings.add_warning.return_value = 2
    mock_dbguild.return_value = mock_guild_instance

    mock_botapp.rest.fetch_guild = AsyncMock()
    mock_botapp.rest.fetch_guild.return_value = MagicMock(name="FailGuild")
    mock_botapp.rest.fetch_guild.return_value.name = "FailGuild"

    mock_user = MagicMock()
    mock_user.id = 111
    mock_user.mention = "@Ame"
    mock_user.send = AsyncMock(side_effect=hikari.ForbiddenError.__new__(hikari.ForbiddenError))

    mock_responder = AsyncMock()

    ds.d["guild_name_cache"] = {}

    await handle_warn_user(
        guild_id=123,
        user=mock_user,
        reason="Still bad",
        responder_func=mock_responder
    )

    # DM attempted
    mock_user.send.assert_called_once()

    # Warning still recorded
    mock_guild_instance.warnings.add_warning.assert_called_once()

    # Embed includes "No Notification"
    args, kwargs = mock_responder.call_args
    embed = args[0]
    assert any(field.name == "No Notification" for field in embed.fields)


@pytest.mark.asyncio
@patch("modules.moderation.warnings.add_warning.dbguild")
@patch("modules.moderation.warnings.add_warning.botapp")
async def test_warn_uses_cached_guild_name(mock_botapp, mock_dbguild):
    mock_guild_instance = MagicMock()
    mock_guild_instance.warnings.add_warning.return_value = 3
    mock_dbguild.return_value = mock_guild_instance

    mock_user = MagicMock()
    mock_user.id = 222
    mock_user.mention = "@Ame"
    mock_user.send = AsyncMock()

    mock_responder = AsyncMock()

    # Insert valid cache entry
    ds.d["guild_name_cache"] = {
        123: {
            "name": "CachedGuild",
            "time": datetime.datetime.now().timestamp()
        }
    }

    await handle_warn_user(
        guild_id=123,
        user=mock_user,
        reason="Cached reason",
        responder_func=mock_responder
    )

    # Should NOT fetch from Discord
    mock_botapp.rest.fetch_guild.assert_not_called()