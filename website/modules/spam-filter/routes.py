from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from library.database.guilds import dbguild
from fastapi import APIRouter, Request
from website import memory as webdb
from markupsafe import Markup
import json
import os

router = APIRouter()

module_templates_path = os.path.join(os.path.dirname(__file__), "templates")
shared_templates_path = os.path.join("website", "modules", "shared", "templates")

env = Environment(
    loader=ChoiceLoader([
        FileSystemLoader(module_templates_path),
        FileSystemLoader(shared_templates_path),
    ])
)
templates = Jinja2Templates(env=env)

def _tojson_filter(value):
    return Markup(json.dumps(value))

env.filters["tojson"] = _tojson_filter

@router.get("/dashboard/{guild_id}/spam-filter")
async def show_page(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
        }
    )

@router.post("/api/guild/{guild_id}/modules/set-penalty/spam")
async def set_text_penalties(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    data: dict = await request.json()
    guild = dbguild(guild_id)

    for item_name in data.keys():
        if item_name == "do-ban":
            guild.set.spam.do_ban_member(data[item_name])
        elif item_name == "do-kick":
            guild.set.spam.do_kick_member(data[item_name])
        elif item_name == "do-delete":
            guild.set.spam.do_delete_msg(data[item_name])
        elif item_name == "do-cooldown":
            guild.set.spam.do_cooldown(data[item_name])
        elif item_name == "do-warnings":
            guild.set.spam.do_warn_member(data[item_name])
        elif item_name == "do-mutes":
            guild.set.spam.do_mute_member(data[item_name])
        elif item_name == "do-announcement":
            guild.set.spam.do_announce_infraction(data[item_name])
        elif item_name == "do-ban_announcement":
            guild.set.spam.do_announce_ban(data[item_name])
        elif item_name == "do-kick_announcement":
            guild.set.spam.do_announce_kick(data[item_name])
        else:
            raise HTTPException("This item name is not known.", status_code=400)

@router.get("/api/guild/{guild_id}/modules/get-penalty/spam")
async def set_text_penalties(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    guild = dbguild(guild_id)

    return JSONResponse(
        {
            "do-ban": guild.get.spam.do_ban_member(),
            "do-kick": guild.get.spam.do_kick_member(),
            "do-delete": guild.get.spam.do_delete_msg(),
            "do-cooldown": guild.get.spam.do_cooldown(),
            "do-warnings": guild.get.spam.do_warn_member(),
            "do-mutes": guild.get.spam.do_warn_member(),
            "do-announcement": guild.get.spam.do_announce_infraction(),
            "do-ban_announcement": guild.get.spam.do_announce_ban(),
            "do-kick_announcement": guild.get.spam.do_announce_kick(),
        }
    )