from library.permissions import prechecks, cooldowns, perms
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import lightbulb
import pytest
import hikari



# Mock datastore
@pytest.fixture(autouse=True)
def mock_ds(monkeypatch):
    mock_data = {
        "cooldowns": {},
        "cmd_cooldowns_memory": {},
        "guild_owner_ids_cache": {}
    }
    monkeypatch.setattr("library.permissions.ds.d", mock_data)
    return mock_data

# Mock botapp
@pytest.fixture(autouse=True)
def mock_botapp(monkeypatch):
    mock_app = MagicMock()
    mock_app.heartbeat_latency = 0.1
    mock_app.rest.fetch_member = AsyncMock()
    mock_app.cache.get_guild = MagicMock(return_value=None)
    mock_app.rest.fetch_guild = AsyncMock()
    monkeypatch.setattr("library.permissions.botapp", mock_app)
    return mock_app

# Mock context
@pytest.fixture
def ctx():
    user = MagicMock()
    user.id = 123
    guild = 456
    ctx = MagicMock(spec=lightbulb.Context)
    ctx.user = user
    ctx.guild_id = guild
    ctx.defer = AsyncMock()
    ctx.respond = AsyncMock()
    return ctx

@pytest.mark.asyncio
async def test_cooldown_start_and_check(mock_ds):
    cd = cooldowns(user_id=1)
    assert cd.start_cooldown("test_cmd", 5) is True

    # Immediately, the command should be on cooldown
    wait_time = cd.cmd_cooled("test_cmd")
    assert wait_time < 0  # still waiting

    # After expiration
    mock_ds['cooldowns'][1]["test_cmd"] = datetime.now().timestamp() - 1
    assert cd.cmd_cooled("test_cmd") is True

@pytest.mark.asyncio
async def test_is_privileged_allows_if_none_permission(ctx):
    result = await perms.is_privileged(None, ctx.guild_id, ctx.user.id)
    assert result is True

@pytest.mark.asyncio
async def test_prechecks_permission_denied(ctx):
    with patch("library.permissions.perms.is_privileged", new=AsyncMock(return_value=False)):
        with pytest.raises(perms.errors.user_perm_error):
            await prechecks("cmd1", ctx, permission=hikari.Permissions.MANAGE_GUILD)

@pytest.mark.asyncio
async def test_prechecks_cooldown_active(ctx, mock_ds):
    # Start cooldown
    cd = cooldowns(ctx.user.id)
    cd.start_cooldown("cmd2", 5)

    # Patch cooldowns to use the same user
    with patch("library.permissions.cooldowns", return_value=cd):
        with pytest.raises(perms.errors.cooldown_active):
            await prechecks("cmd2", ctx, cooldown_s=5)

@pytest.mark.asyncio
async def test_prechecks_bot_admin(ctx):
    from library.settings import get
    # Patch get.primary_maintainer to be the user
    with patch.object(get, "primary_maintainer", return_value=ctx.user.id):
        result = await prechecks("admin_cmd", ctx, bot_admin_only=True)
        assert result is True

@pytest.mark.asyncio
async def test_get_user_permissions_owner(ctx, mock_botapp, mock_ds):
    # Set guild owner
    mock_ds['guild_owner_ids_cache'][ctx.guild_id] = ctx.user.id

    # Make fetch_member return a member with the correct ID
    mock_member = MagicMock()
    mock_member.id = ctx.user.id
    mock_member.fetch_roles = AsyncMock(return_value=[])
    mock_botapp.rest.fetch_member.return_value = mock_member

    perms_list = await perms.get_user_permissions(ctx.guild_id, ctx.user.id)
    assert hikari.Permissions.ADMINISTRATOR in perms_list

@pytest.mark.asyncio
async def test_get_guild_owner_id_fetch(ctx, mock_botapp, mock_ds):
    # Clear cache
    mock_ds['guild_owner_ids_cache'].pop(ctx.guild_id, None)
    mock_guild = MagicMock()
    mock_guild.owner_id = 999
    mock_botapp.cache.get_guild.return_value = mock_guild

    owner_id = await perms.get_guild_owner_id(ctx.guild_id)
    assert owner_id == 999
    assert mock_ds['guild_owner_ids_cache'][ctx.guild_id] == 999