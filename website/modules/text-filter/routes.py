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

@router.get("/dashboard/{guild_id}/text-filter")
async def show_page(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    guild = dbguild(guild_id)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
            "do-escalate": guild.get.do_escalate(),
            "escalation_settings": {
                "del_msg": guild.get.text.escalation.msg_deletion(),
                "cooldown": guild.get.text.escalation.cooldown_threshold(),
                "mute": guild.get.text.escalation.mute_threshold(),
                "kick": guild.get.text.escalation.kick_member(),
                "ban": guild.get.text.escalation.ban_member(),                
            }
        }
    )

@router.post("/api/text-filter/{guild_id}/set-escalation")
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

    cat_set = guild.set.text

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

@router.post("/api/guild/{guild_id}/modules/set-penalty/text")
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
            guild.set.text.do_ban_member(data[item_name])
        elif item_name == "do-kick":
            guild.set.text.do_kick_member(data[item_name])
        elif item_name == "do-delete":
            guild.set.text.do_delete_msg(data[item_name])
        elif item_name == "do-cooldown":
            guild.set.text.do_cooldown(data[item_name])
        elif item_name == "do-warnings":
            guild.set.text.do_warn_member(data[item_name])
        elif item_name == "do-mutes":
            guild.set.text.do_mute_member(data[item_name])
        elif item_name == "do-announcement":
            guild.set.text.do_announce_infraction(data[item_name])
        elif item_name == "do-ban_announcement":
            guild.set.text.do_announce_ban(data[item_name])
        elif item_name == "do-kick_announcement":
            guild.set.text.do_announce_kick(data[item_name])
        elif item_name == "do-escalation":
            guild.set.do_escalate(data[item_name])
        else:
            raise HTTPException("This item name is not known.", status_code=400)

    return HTMLResponse("Done", 200)

@router.get("/api/guild/{guild_id}/modules/get-penalty/text")
async def get_text_penalties(request: Request, guild_id:int):
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
            "do-ban": guild.get.text.do_ban_member(),
            "do-kick": guild.get.text.do_kick_member(),
            "do-delete": guild.get.text.do_delete_msg(),
            "do-cooldown": guild.get.text.do_cooldown(),
            "do-warnings": guild.get.text.do_warn_member(),
            "do-mutes": guild.get.text.do_warn_member(),
            "do-announcement": guild.get.text.do_announce_infraction(),
            "do-ban_announcement": guild.get.text.do_announce_ban(),
            "do-kick_announcement": guild.get.text.do_announce_kick(),
            "do-escalation": guild.get.do_escalate()
        }
    )