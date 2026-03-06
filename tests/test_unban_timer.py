import modules.auto_tasks.unban_timer as unban_timer
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import pytest
import hikari

# Example ban object for mocking
class MockBan:
    def __init__(self, guild_id, banned_id, moderator_id, expire_seconds):
        self.guild_id = guild_id
        self.banned_id = banned_id
        self.moderator_id = moderator_id
        self.time_to_unban = datetime.now() - timedelta(seconds=expire_seconds)

@pytest.mark.asyncio
async def test_handle_task_unbans_success_and_failure(monkeypatch):
    # Create bans: one expired (success), one expired (failure), one in the future
    success_ban = MockBan(1, 100, 200, expire_seconds=10)
    fail_ban = MockBan(1, 101, 201, expire_seconds=5)
    future_ban = MockBan(1, 102, 202, expire_seconds=-1000)

    # Mock list_all_bans
    monkeypatch.setattr(
        "modules.auto_tasks.unban_timer.list_all_bans",
        lambda: [success_ban, fail_ban, future_ban]
    )

    # Mock guild
    mock_guild = MagicMock()
    # success_ban unbans successfully, fail_ban fails (returns False)
    async def mock_unban(user_id, reason):
        if user_id == success_ban.banned_id:
            return True
        elif user_id == fail_ban.banned_id:
            return False
        return True
    mock_guild.bans.unban_user = AsyncMock(side_effect=mock_unban)
    monkeypatch.setattr("modules.auto_tasks.unban_timer.dbguild", lambda guild_id: mock_guild)

    # Mock server logs
    mock_logs = MagicMock()
    monkeypatch.setattr("modules.auto_tasks.unban_timer.server_logs", lambda guild_id: mock_logs)

    # Run the task
    await unban_timer.handle_task()

    # Check successful unban
    mock_guild.bans.unban_user.assert_any_await(
        user_id=success_ban.banned_id,
        reason=f"Ban countdown as set by user with ID {success_ban.moderator_id} had expired"
    )

    # Check failed unban
    mock_guild.bans.unban_user.assert_any_await(
        user_id=fail_ban.banned_id,
        reason=f"Ban countdown as set by user with ID {fail_ban.moderator_id} had expired"
    )

    # Future ban should NOT be unbanned
    assert mock_guild.bans.unban_user.await_count == 2

    # Log should have been created for the failed unban
    assert mock_logs.create_entry.call_count == 2
    embed_arg = mock_logs.create_entry.call_args[0][0]
    assert isinstance(embed_arg, hikari.Embed)
    assert "Unban Failed" in embed_arg.title
    assert str(fail_ban.banned_id) in embed_arg.description