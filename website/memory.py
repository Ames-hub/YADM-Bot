from library.database.manage import get_session, web_guild_session, user_web_session
from datetime import datetime, timedelta, timezone
from cachetools import TTLCache
from library import web_rest
import hikari

guild_cache = TTLCache(maxsize=1, ttl=300)
async def get_my_guilds():
    if "guilds" in guild_cache:
        return guild_cache["guilds"]

    rest = web_rest.get_rest()
    data = await rest.fetch_my_guilds()  # This gets the bot's guilds

    guild_cache["guilds"] = data

    return data

def verify_session(session_id:int):
    with get_session() as session:
        user_session = (
            session.query(user_web_session)
            .filter(user_web_session.session_id == session_id)
            .one_or_none()
        )
        if not user_session:
            return False

        if user_session.expires_at <= datetime.now():
            session.delete(user_session)
            records = (
                session.query(web_guild_session)
                .filter(web_guild_session.session_id == session_id)
                .all()
            )
            session.delete(records)
            session.commit()
            return False
    return user_session is not None

def get_user_session(user_id:int=None, session_id=None) -> user_web_session:
    with get_session() as session:
        user_session = (
            session.query(user_web_session)
            
        )
        if user_id:
            user_session.filter(user_web_session.discord_user_id == user_id)
        else:
            user_session.filter(user_web_session.session_id == session_id)

        user_session = user_session.one_or_none()

        if not user_session:
            return None

        if user_session.expires_at <= datetime.now():
            session.delete(user_session)
            records = (
                session.query(web_guild_session)
                .filter(web_guild_session.session_id == user_session.session_id)
                .all()
            )
            session.delete(records)
            session.commit()
            return None
        return user_session

making_session_cache = TTLCache(maxsize=10000, ttl=10)
def create_guild_sessions(session_id: str, discord_user_id: int, username: str, guild: int, guild_name:str, perms_mask:int, is_owner:bool, lifetime_days: int = 7) -> str:
    """
    Creates a new web session row and returns the session_id (as a string) to be
    stored in the client's session_id cookie.
    """
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=lifetime_days)

    with get_session() as db_session:
        if making_session_cache.get(str(discord_user_id), True):
            db_session.add(
                user_web_session(
                    session_id=session_id,
                    discord_user_id=discord_user_id,
                    expires_at=expires_at,
                    username=username,
                )
            )
            db_session.commit()
            making_session_cache[str(discord_user_id)] = False  # This prevents an attempt to make multiple user_web_sessions.
        db_session.add(
            web_guild_session(
                session_id=session_id,
                guild=guild,
                perms_mask=perms_mask,
                is_owner=is_owner,
                guild_name=guild_name
            )
        )
        db_session.commit()

    return session_id

def remove_guild_session(guild_id:int, session_id:str=None, discord_user_id: int=None):
    with get_session() as session:
        records = session.query(web_guild_session).filter(web_guild_session.guild == guild_id)
        if session_id:
            records = records.filter(web_guild_session.session_id == session_id)
        if discord_user_id:
            records = records.filter(web_guild_session.discord_user_id == discord_user_id)
        records = records.all()
        if records:
            session.delete(records)
            session.commit()
            return True
        else:
            return False

def fetch_guild_session(session_id:str, guild_id: int, delete_old:bool=True) -> web_guild_session:
    with get_session() as session:
        record = (
            session.query(web_guild_session)
            .filter(web_guild_session.session_id == session_id)
            .filter(web_guild_session.guild == guild_id)
            .one_or_none()
        )
        if not record:
            return None
        if delete_old:
            user_session = (
                session.query(user_web_session)
                .filter(user_web_session.session_id == session_id)
                .one_or_none()
            )

            if user_session.expires_at < datetime.now():
                records = (
                    session.query(web_guild_session)
                    .filter(web_guild_session.session_id == session_id)
                    .all()
                )
                session.delete(user_session)
                session.delete(records)
                session.commit()
                return None
        return record

manageable_guilds_cache = TTLCache(maxsize=1000, ttl=300)
async def determine_manageable_guilds(session_id:str=None, user_id:int=None, ids_only:bool=True) -> list:
    if user_id and session_id:
        raise ValueError("Both user ID and Session ID cannot be provided at the same time.")

    if user_id:
        if manageable_guilds_cache.get(str(user_id), None):
            if manageable_guilds_cache[user_id][1] == ids_only:
                return manageable_guilds_cache[str(user_id)][0]
    else:
        if manageable_guilds_cache.get(session_id, None):
            if manageable_guilds_cache[session_id][1] == ids_only:
                return manageable_guilds_cache[session_id][0]

    user_session = get_user_session(user_id=user_id)
    if not user_session:
        return False

    my_guilds_ids = [guild.id for guild in await get_my_guilds()]

    with get_session() as session:
        records = (
            session.query(web_guild_session)
            .filter(web_guild_session.session_id == user_session.session_id)
            .all()
        )
        manageable = []
        if ids_only:
            for record in records:
                if record.guild not in my_guilds_ids:
                    continue
                if record.is_owner:
                    manageable.append(record.guild)
                elif record.perms_mask & hikari.Permissions.ADMINISTRATOR:
                    manageable.append(record.guild)
        else:
            for record in records:
                if record.guild not in my_guilds_ids:
                    continue
                if record.is_owner:
                    manageable.append(record)
                elif record.perms_mask & hikari.Permissions.ADMINISTRATOR:
                    manageable.append(record)

        if user_id:
            manageable_guilds_cache[str(user_id)] = (manageable, ids_only)
        else:
            manageable_guilds_cache[str(session_id)] = (manageable, ids_only)
    return manageable