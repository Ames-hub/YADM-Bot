from jinja2 import ChoiceLoader, FileSystemLoader, Environment
from fastapi.templating import Jinja2Templates
from library.database.guilds import dbguild
from fastapi import APIRouter, Request
from website import management
from markupsafe import Markup
import hikari
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

@router.get("/dashboard/{guild_id}/violations-log")
@management.guild_prechecks([hikari.Permissions.VIEW_AUDIT_LOG])
async def show_page(request: Request, guild_id:int):
    guild = dbguild(guild_id)
    violations_log = guild.get_member_violations()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guild_id": guild_id,
            "violations_log": violations_log
        }
    )