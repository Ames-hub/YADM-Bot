from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from library.mainydb import guild_icons
from fastapi import APIRouter, Request
from library.web_rest import get_rest
from website import memory as db
import aiohttp
import hikari
import os

router = APIRouter()

module_templates_path = os.path.join(os.path.dirname(__file__), "templates")
shared_templates_path = os.path.join("modules", "shared", "templates")

env = Environment(
    loader=ChoiceLoader([
        FileSystemLoader(module_templates_path),
        FileSystemLoader(shared_templates_path),
    ])
)

templates = Jinja2Templates(env=env)

@router.get("/list")
async def show_page(request: Request):
    session_id = request.cookies.get("session_id")
    if not db.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")

    managed_guilds: list[db.web_guild_session] = await db.determine_manageable_guilds(session_id=session_id, ids_only=False)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "server_list": managed_guilds
        }
    )

with open("library/placeholder-guild.png", "rb") as f:
    placeholder_guild = f.read()

@router.get("/api/{guild_id}/server-icon")
async def get_icon(guild_id: int):
    img = guild_icons.get_img(guild_id)

    if img:
        return Response(content=img, media_type="image/png")

    rest = get_rest()

    try:
        guild = await rest.fetch_guild(guild_id)
    except (hikari.NotFoundError, hikari.ForbiddenError):
        guild_icons.archive_img(guild_id, placeholder_guild)
        return Response(placeholder_guild, media_type="image/png")

    if not guild.icon_hash:
        guild_icons.archive_img(guild_id, placeholder_guild)
        return Response(placeholder_guild, media_type="image/png")

    icon_url = guild.make_icon_url(file_format="PNG").url

    # Download the actual image
    async with aiohttp.ClientSession() as session:
        async with session.get(icon_url) as response:
            if response.status != 200:
                guild_icons.archive_img(guild_id, placeholder_guild)
                return Response(placeholder_guild, media_type="image/png")

            img = await response.read()

    guild_icons.archive_img(guild_id, img)

    return Response(content=img, media_type="image/png")