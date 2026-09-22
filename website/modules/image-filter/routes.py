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

@router.get("/dashboard/{guild_id}/image-filter")
async def show_page(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    guild = dbguild(guild_id)

    escalation_settings = {
        "del_msg": guild.get.images.escalation.msg_deletion(),
        "cooldown": guild.get.images.escalation.cooldown_threshold(),
        "mute": guild.get.images.escalation.mute_threshold(),
        "kick": guild.get.images.escalation.kick_member(),
        "ban": guild.get.images.escalation.ban_member(),                
    }
    do_escalate = guild.get.do_escalate()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
            "do-escalate": do_escalate,
            "escalation_settings": escalation_settings
        }
    )

@router.post("/api/guild/{guild_id}/modules/set-penalty/image")
async def set_image_penalties(request: Request, guild_id:int):
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
            guild.set.images.do_ban_member(data[item_name])
        elif item_name == "do-kick":
            guild.set.images.do_kick_member(data[item_name])
        elif item_name == "do-delete":
            guild.set.images.do_delete_msg(data[item_name])
        elif item_name == "do-cooldown":
            guild.set.images.do_cooldown(data[item_name])
        elif item_name == "do-warnings":
            guild.set.images.do_warn_member(data[item_name])
        elif item_name == "do-mutes":
            guild.set.images.do_mute_member(data[item_name])
        elif item_name == "do-announcement":
            guild.set.images.do_announce_infraction(data[item_name])
        elif item_name == "do-ban_announcement":
            guild.set.images.do_announce_ban(data[item_name])
        elif item_name == "do-kick_announcement":
            guild.set.images.do_announce_kick(data[item_name])
        elif item_name == "do-escalation":
            guild.set.do_escalate(data[item_name])
        else:
            raise HTTPException("This item name is not known.", status_code=400)

    return HTMLResponse("Done", 200)

@router.get("/api/guild/{guild_id}/modules/get-penalty/image")
async def get_image_penalties(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    guild = dbguild(guild_id)
    response_data = {
        "do-ban": guild.get.images.do_ban_member(),
        "do-kick": guild.get.images.do_kick_member(),
        "do-delete": guild.get.images.do_delete_msg(),
        "do-cooldown": guild.get.images.do_cooldown(),
        "do-warnings": guild.get.images.do_warn_member(),
        "do-mutes": guild.get.images.do_warn_member(),
        "do-announcement": guild.get.images.do_announce_infraction(),
        "do-ban_announcement": guild.get.images.do_announce_ban(),
        "do-kick_announcement": guild.get.images.do_announce_kick(),
    }

    return JSONResponse(response_data, status_code=200)

@router.post("/api/image-filter/{guild_id}/set-escalation")
async def set_bot_escalation(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    data: dict = await request.json()
    guild = dbguild(guild_id)

    successes = []

    cat_set = guild.set.images

    for item_name in data.keys():
        value = data[item_name]
        if item_name == "do-ban":
            if value:
                ok = cat_set.escalation.ban_member(data[item_name])
            else:
                ok = cat_set.do_ban_member(False)
            successes.append(ok)
        elif item_name == "do-cooldown":
            if value:
                ok = cat_set.escalation.cooldown_threshold(value)
            else:
                ok = cat_set.do_cooldown(False)
            successes.append(ok)
        elif item_name == "do-delete": 
            if value:
                ok = cat_set.escalation.msg_deletion(data[item_name])
            else:
                ok = cat_set.do_delete_msg(False)
            successes.append(ok)
        elif item_name == "do-kick":
            if value:
                ok = cat_set.escalation.kick_member(data[item_name])
            else:
                ok = cat_set.do_kick_member(False)
            successes.append(ok)
        elif item_name == "do-mutes":
            if value:
                ok = cat_set.escalation.mute_threshold(data[item_name])
            else:
                ok = cat_set.do_mute_member(False)
            successes.append(ok)
        else:
            raise HTTPException(400, "That option does not exist.")

    return HTMLResponse(
        "Operation completed. See code for success.",
        status_code=200 if all(successes) else 500
    )