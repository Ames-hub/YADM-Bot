from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Request
from urllib.parse import urlencode
from library import settings
import secrets
import httpx
import os

router = APIRouter()

module_templates_path = os.path.join(os.path.dirname(__file__), "templates")
shared_templates_path = os.path.join("modules", "shared", "templates")

@router.get("/auth/discord/login")
async def discord_login(request: Request):
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state  # or a temp cookie/DB row — CSRF protection

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
        guilds = (await client.get("https://discord.com/api/users/@me/guilds", headers=headers)).json()
    # access_token goes out of scope here and is never persisted

    # cross-reference against bot's guilds table, filter to admin-permission ones
    manageable_guild_ids = await get_manageable_guilds(user["id"], guilds)

    session_id = await create_session(user_id=user["id"], username=user["username"], avatar=user["avatar"])
    response = RedirectResponse("/dashboard")
    response.set_cookie(
        "session_id", session_id,
        httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 24 * 7,
    )
    return response