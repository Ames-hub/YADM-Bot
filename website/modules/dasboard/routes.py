from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
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
    )