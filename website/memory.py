from library.database.manage import get_session, web_session
from datetime import datetime, timedelta, timezone
from cachetools import TTLCache
from library import web_rest
import hikari
import uuid

guild_cache = TTLCache(maxsize=1, ttl=120)
async def get_my_guilds():
    if "guilds" in guild_cache:
        return guild_cache["guilds"]

    rest = web_rest.get_rest()
    data = await rest.fetch_my_guilds()

    guild_cache["guilds"] = data

    return data

def create_session(discord_user_id: int, username: str, in_guilds: str = "", lifetime_days: int = 7) -> str:
    """
    Creates a new web session row and returns the session_id (as a string) to be
    stored in the client's session_id cookie.
    """
    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=lifetime_days)

    with get_session() as db_session:
        db_session.add(
            web_session(
                session_id=session_id,
                discord_user_id=discord_user_id,
                username=username,
                expires_at=expires_at,
                in_guilds=in_guilds,
            )
        )
        db_session.commit()

    return session_id

def fetch_session(session_id:str, delete_old:bool=True):
    with get_session() as session:
        record = (
            session.query(web_session)
            .filter(web_session.session_id == session_id)
            .one_or_none()
        )
        if not record:
            return None
        if delete_old:
            if record.expires_at < datetime.now():
                session.delete(record)
                session.commit()
                return None
        return record

async def determine_manageable_guilds(user_id: int, guilds: list[dict]) -> list:
    with get_session() as db_session:
        manageable = []
        my_guilds = [guild.id for guild in await get_my_guilds()]

        for guild_item in guilds.split(","):
            g_split = guild_item.split("|")
            guild_id = int(g_split[0])
            if not guild_id in my_guilds:
                continue
            perms_int = int(g_split[1])
            owns_guild = bool(g_split[2])
            has_admin = perms_int & hikari.Permissions.ADMINISTRATOR
            if has_admin or owns_guild:
                manageable.append(guild_id)

        return manageable