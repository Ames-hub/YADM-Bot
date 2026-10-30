from fastapi.responses import RedirectResponse
from fastapi import Request, HTTPException
from website import memory as webdb
from functools import wraps
import hikari

def guild_prechecks(permissions: list[hikari.Permissions] = None):
    permissions = permissions or []

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, guild_id: int, *args, **kwargs):
            session_id = request.cookies.get("session_id")

            if not webdb.verify_session(session_id):
                return RedirectResponse("/auth/discord/login")

            session = webdb.fetch_guild_session(
                session_id=session_id,
                guild_id=guild_id
            )

            if not session:
                raise HTTPException(401, "Invalid session.")

            managed_guilds = await webdb.determine_manageable_guilds(
                session_id=session.session_id
            )

            if guild_id not in managed_guilds:
                raise HTTPException(
                    403,
                    "You cannot manage servers you do not own, or are not an admin of."
                )

            if permissions:
                # Combines all required permissions into one mask.
                needed_perms = 0
                for permission in permissions:
                    needed_perms |= permission

                # Check permissions
                guild_session = webdb.get_guild_session(
                    guild_id=guild_id,
                    session_id=session_id
                )

                if not guild_session:
                    raise HTTPException(401, "Missing guild session.")

                if (guild_session.perms_mask & needed_perms) != needed_perms:
                    raise HTTPException(403, "Insufficient permissions.")

            return await func(request, guild_id, *args, **kwargs)

        return wrapper

    return decorator