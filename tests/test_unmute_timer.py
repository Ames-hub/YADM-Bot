from unittest.mock import AsyncMock, patch, MagicMock
from library.database.manage import mute_record
from datetime import datetime
import pytest

# Import your actual module here
from modules.auto_tasks.unmute_timer import handle_task

@pytest.mark.asyncio
@patch("modules.auto_tasks.unmute_timer.muting.set_mute_inactive")
@patch("modules.auto_tasks.unmute_timer.muting.list_all_mutes")
@patch("modules.auto_tasks.unmute_timer.dbguild")
@patch("modules.auto_tasks.unmute_timer.botapp")
@patch("modules.auto_tasks.unmute_timer.ds")
async def test_handle_task_unmute(
    mock_ds,
    mock_botapp,
    mock_dbguild,
    mock_list_all_mutes,
    mock_set_mute_inactive,
):
    # Setup: one mute that is due
    user_id = 123
    guild_id = 456
    case_id = 1
    scheduled_unmute = datetime.now().timestamp() - 1  # already expired

    mock_list_all_mutes.return_value = [
        mute_record(
            user_id=user_id,
            guild_id=guild_id,
            case_id=case_id,
            scheduled_unmute=scheduled_unmute,
            active=True,
            reason="Test Mute"
        )
    ]

    # Mock guild
    mock_guild_instance = MagicMock()
    mock_guild_instance.get.muted_role_id.return_value = 999
    mock_dbguild.return_value = mock_guild_instance

    # Mock botapp rest methods
    mock_botapp.rest.remove_role_from_member = AsyncMock()
    mock_user = AsyncMock()
    mock_user.send = AsyncMock()
    mock_botapp.rest.fetch_user = AsyncMock(return_value=mock_user)
    mock_botapp.rest.fetch_guild = AsyncMock()
    
    # Mock datastore
    mock_ds.d = {"guild_name_cache": {}}

    # Run the task
    await handle_task()

    # Assertions
    mock_botapp.rest.remove_role_from_member.assert_awaited_once_with(
        guild=guild_id, user=user_id, role=999
    )
    mock_botapp.rest.fetch_user.assert_awaited_once_with(user_id)
    mock_user.send.assert_awaited_once()
    mock_set_mute_inactive.assert_called_once_with(case_id)