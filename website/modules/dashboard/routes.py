from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import Response
from fastapi import APIRouter, Request
from website import memory as db
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
    session = db.fetch_session(request.cookies.get("session_id"))
    if not session:
        raise HTTPException(401, "Session required.")
    managed_guilds = await db.determine_manageable_guilds(session.discord_user_id, session.in_guilds)

    if guild_id not in managed_guilds:
        raise HTTPException(403, "You cannot manage servers you do not own, or are not an admin of.")

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            # TODO: Change this to use proper data, not test data.
            "stat_list": [  # If you add another here, be sure to update the route "/api/get-statistic/{stat_name}/svg" below too.
                {
                    # For the name, naming conventions are all lower-case. It will have "str.upper()" applied on the webui.
                    "name": "violations",
                    "datums": [
                        {"title": "Daily", "value": 0}, 
                        {"title": "Weekly", "value": 0}, 
                        {"title": "Monthly", "value": 0}
                    ]
                },
                {
                    "name": "chats flagged",
                    "datums": [
                        {"title": "Daily", "value": 0}, 
                        {"title": "Weekly", "value": 0}, 
                        {"title": "Monthly", "value": 0}
                    ]
                },
                {
                    "name": "bans issued",
                    "datums": [
                        {"title": "Daily", "value": 0}, 
                        {"title": "Weekly", "value": 0}, 
                        {"title": "Monthly", "value": 0}
                    ]
                },
                {
                    "name": "kicks issued",
                    "datums": [
                        {"title": "Daily", "value": 0}, 
                        {"title": "Weekly", "value": 0}, 
                        {"title": "Monthly", "value": 0}
                    ]
                },
                {
                    "name": "mutes issued",
                    "datums": [
                        {"title": "Daily", "value": 0}, 
                        {"title": "Weekly", "value": 0}, 
                        {"title": "Monthly", "value": 0}
                    ]
                },
            ]
        }
    )

paths = {
    "violations": open("website/modules/shared/templates/svgs/warning-shield.svg", "rb").read(),
    "bans issued": open("website/modules/shared/templates/svgs/gavel.svg").read(),
    "kicks issued": open("website/modules/shared/templates/svgs/gavel.svg").read(),
    "mutes issued": open("website/modules/shared/templates/svgs/silenced.svg").read(),
    "chats flagged": open("website/modules/shared/templates/svgs/message.svg").read(),
}

@router.get("/api/get-statistic/{stat_name}/svg")
async def return_stat_svg(stat_name):
    """
    Gets a stat by name, gets its image.
    """
    return Response(paths[stat_name], 200, media_type="image/svg+xml")