from library.database.guilds import dbguild, violations, member_violation
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Request
from library.web_rest import get_rest
from website import memory as webdb
from cachetools import TTLCache
from datetime import datetime
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

username_cache = TTLCache(maxsize=5000, ttl=21600)
async def find_username(user_id:int, prefer_display:bool=False):
    if username_cache.get(user_id, None) is None:
        rest = get_rest()
        user = await rest.fetch_user(user_id)
        username_cache[user_id] = {"name": user.username, "display": user.display_name}
        if prefer_display:
            return user.display_name
        else:
            return user.username
    else:
        data = username_cache.get(user_id)
        if prefer_display:
            return data["display"]
        else:
            return data["name"]

@router.get("/dashboard/{guild_id}")
async def show_page(request: Request, guild_id:int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")
    
    session = webdb.fetch_guild_session(session_id=request.cookies.get("session_id"), guild_id=guild_id)
    managed_guilds = await webdb.determine_manageable_guilds(session_id=session.session_id)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    guild = dbguild(guild_id)
    violation_list: list[member_violation] = violations.get_violations_by_guild(guild_id)

    today_violations = 0
    weekly_violations = 0

    yesterday_posix = int(datetime.now().timestamp() - 86400)
    last_week_posix = int(datetime.now().timestamp() - 604800)
    for violation in violation_list:
        violation_posix = violation.time.timestamp()
        if violation_posix <= last_week_posix:
            weekly_violations += 1
        elif violation_posix <= yesterday_posix:
            today_violations += 1

    total_violations = len(violation_list)

    unban_today = 0
    unban_next_week = 0
    all_bans = guild.bans.list_bans(active_only=True)
    for ban in all_bans:
        if ban.time_to_unban <= 86400:  # one day
            unban_today += 1
        elif ban.time_to_unban <= 604800:  # one week
            unban_next_week += 1

    unmute_today = 0
    unmute_next_week = 0
    all_mutes = guild.muting.list_mutes(active_only=True)
    for mute in all_mutes:
        if mute.scheduled_unmute <= 86400:  # one day
            unmute_today += 1
        if mute.scheduled_unmute <= 604800:  # one week
            unmute_next_week += 1

    do_text_scan = guild.get.do_text_scan()
    do_spam_scan = guild.get.do_filter_spam()
    do_image_scan = guild.get.do_image_filtering()
    guild_warnings = guild.warnings.get_all(newest_first=False, limit=50)

    # We need to add the usernames to the warning items.
    for item in guild_warnings:
        warned_name = await find_username(item.user_id, prefer_display=True)
        mod_name = await find_username(item.moderator_id, prefer_display=True)
        setattr(item, "warned_name", warned_name)
        setattr(item, "moderator_name", mod_name)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
            "guild_warnings": guild_warnings,
            "stat_list": [  # If you add another here, be sure to update the route "/api/get-statistic/{stat_name}/svg" below too.
                {
                    # For the name, naming conventions are all lower-case. It will have "str.upper()" applied on the webui.
                    "name": "modules",
                    "datums": [
                        {"title": "Text Filter", "value": "Online" if do_text_scan else "Offline"},
                        {"title": "Anti-Spam", "value": "Online" if do_spam_scan else "Offline"},
                        {"title": "Image Filter", "value": "Online" if do_image_scan else "Offline"},
                    ]
                },
                {
                    "name": "violations",
                    "datums": [
                        {"title": "Daily", "value": today_violations}, 
                        {"title": "Weekly", "value": weekly_violations}, 
                        {"title": "Lifetime", "value": total_violations}
                    ]
                },
                {
                    "name": "unbans pending",
                    "datums": [
                        {"title": "<= 24 hours", "value": unban_today}, 
                        {"title": "<= 7 days", "value": unban_next_week}, 
                        {"title": "Total", "value": len(all_bans)}
                    ]
                },
                {
                    "name": "active mutes",
                    "datums": [
                        {"title": "<= 24 hours", "value": unmute_today}, 
                        {"title": "<= 7 days", "value": unmute_next_week}, 
                        {"title": "Total", "value": len(all_mutes)}
                    ]
                },
            ]
        }
    )

paths = {
    "modules": open("website/modules/shared/templates/svgs/shield.svg", "rb").read(),
    "violations": open("website/modules/shared/templates/svgs/warning-shield.svg", "rb").read(),
    "unbans pending": open("website/modules/shared/templates/svgs/gavel.svg", "rb").read(),
    "active mutes": open("website/modules/shared/templates/svgs/silenced.svg", "rb").read(),
}

@router.get("/api/get-statistic/{stat_name}/svg")
async def return_stat_svg(request: Request, stat_name: str):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")

    svg = paths.get(stat_name)

    if svg is None:
        return Response(status_code=404)

    return Response(
        svg,
        status_code=200,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=2592000"
        }
    )

@router.post("/api/guild/{guild_id}/modules/toggle/{module_name}/{state}")
async def toggle_module(request: Request, guild_id:int, module_name:str, state:bool):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")

    guild = dbguild(guild_id)

    if module_name == "text-filter":
        result = guild.set.do_text_scan(bool(state))
    elif module_name == "spam-filter":
        result = guild.set.do_filter_spam(bool(state))
    elif module_name == "img-filter":
        result = guild.set.do_image_filtering(bool(state))
    else:
        raise HTTPException(400, "Incorrect module name")

    return Response(
        content=f"{result}",
        status_code=200 if result else 500,
    )

@router.get("/api/guild/{guild_id}/modules")
async def get_modules(request: Request, guild_id: int):
    session_id = request.cookies.get("session_id")
    if not webdb.verify_session(session_id):
        return RedirectResponse("/auth/discord/login")

    guild = dbguild(guild_id)
    return {
        "text-filter": guild.get.do_text_scan(),
        "spam-filter": guild.get.do_filter_spam(),
        "img-filter": guild.get.do_image_filtering(),
        "link-filter": False,  # TODO: When these are implemented, update the data here.
        "mention-filter": False,
        "raid-protection": False,
    }