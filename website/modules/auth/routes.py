from fastapi.responses import RedirectResponse
from website import memory as db
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Request
from urllib.parse import urlencode
from library import settings
import secrets
import httpx
import uuid

router = APIRouter()

@router.get("/auth/discord/login")
async def discord_login(request: Request):
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    params = {
        "client_id": settings.get.discord_client_id(),
        "redirect_uri": settings.get.discord_redirect_uri(),
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
    }
    return RedirectResponse(f"https://discord.com/oauth2/authorize?{urlencode(params)}")

@router.get("/auth/discord/callback")
async def discord_callback(request: Request, code: str, state: str):
    if state != request.session.get("oauth_state"):
        raise HTTPException(400, "Invalid state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.get.discord_client_id(),
                "client_secret": settings.get.discord_client_secret(),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.get.discord_redirect_uri(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = token_resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        user = (await client.get("https://discord.com/api/users/@me", headers=headers)).json()
        guilds: list[dict] = (await client.get("https://discord.com/api/users/@me/guilds", headers=headers)).json()

    session_id = str(uuid.uuid4())
    for guild in guilds:
        session_id = db.create_guild_sessions(
            session_id=session_id,
            discord_user_id=int(user["id"]),
            username=user["username"],
            guild=guild['id'],
            guild_name=guild['name'],
            perms_mask=guild['permissions'],
            is_owner=guild['owner']
        )
    
    response = RedirectResponse("/list")
    response.set_cookie(
        "session_id", session_id,
        # TODO: This needs to be secure on prod mode, but its fine during development. 
        httponly=True, secure=False, samesite="lax", max_age=60 * 60 * 24 * 7,
    )
    return response