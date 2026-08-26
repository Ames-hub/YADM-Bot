from library.database.guilds import dbguild, violations, member_violation
from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import Response
from fastapi import APIRouter, Request
from website import memory as webdb
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

@router.get("/dashboard/{guild_id}")
async def show_page(request: Request, guild_id:int):
    session = webdb.fetch_session(request.cookies.get("session_id"))
    if not session:
        raise HTTPException(401, "Session required.")
    managed_guilds = await webdb.determine_manageable_guilds(session.discord_user_id, session.in_guilds)

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
        elif mute.scheduled_unmute <= 604800:  # one week
            unmute_next_week += 1

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
            # TODO: Change this to use proper data, not test data.
            "stat_list": [  # If you add another here, be sure to update the route "/api/get-statistic/{stat_name}/svg" below too.
                {
                    # For the name, naming conventions are all lower-case. It will have "str.upper()" applied on the webui.
                    "name": "modules",
                    "datums": [
                        {"title": "Text Filter", "value": guild.get.do_text_scan()},
                        {"title": "Anti-Spam", "value": guild.get.do_filter_spam()},
                        {"title": "Image Filter", "value": guild.get.do_image_filtering()},
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
async def return_stat_svg(stat_name: str):
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