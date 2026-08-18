from fastapi.responses import PlainTextResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from library.database import manage as db
from fastapi import Request, FastAPI
from library import settings
from library import web_rest
import importlib
import datetime
import asyncio
import uvicorn
import logging
import secrets
import sys
import os

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=f"logs/web-{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#==============CONFIG==============#
WEB_PORT = settings.get.web_port()
#============END CONFIG============#

if not settings.get.discord_client_id():
    print("We noticed your Client ID is missing, please go to discord.com/developers/applications, find your applications client ID and provide it.")
    client_id = input("Client ID Here >>> ")
    settings.set.discord_client_id(client_id)
    print("Client ID Saved.")

if not settings.get.discord_client_secret():
    print("We noticed your Client Secret is missing, please go to discord.com/developers/applications, find your applications client secret and provide it.")
    client_secret = input("Client Secret Here >>> ")
    settings.set.discord_client_secret(client_secret)
    print("Client Secret Saved.")

if not settings.get.discord_redirect_uri():
    print("You have not told us your Discord Redirect URI, please enter your pre-set URI now.")
    print("(Should be something like \"http://localhost:8040/auth/discord/callback\")")
    redirect_uri = input("Redirect URI Here >>> ")
    settings.set.discord_redirect_uri(redirect_uri)
    print("Redirect URI saved.")

session_secret_key = secrets.token_urlsafe(64)
settings.set.session_secret_key(session_secret_key)
print("Session secret key generated and saved.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await web_rest.start()
    yield
    await web_rest.stop()

fastapp = FastAPI(lifespan=lifespan)
fastapp.add_middleware(SessionMiddleware, secret_key=settings.get.session_secret_key())

with open('website/robots.txt') as f:
    robots_data = f.read()

@fastapp.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    logging.info(f"{request.client.host} Is asking for the robots.txt")
    return robots_data

with open("yadm-logo.png", "rb") as f:
    web_logo = f.read()

@fastapp.get("/favicon.ico", response_class=PlainTextResponse)
async def get_logo(request: Request):
    return web_logo

@fastapp.get("/", response_class=PlainTextResponse)
async def handle_root(request: Request):
    from website.modules.server_list.routes import show_page
    return await show_page(request)

shared_templates = Jinja2Templates(directory=os.path.join("modules", "shared", "templates"))

# noinspection PyUnusedLocal
@fastapp.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    logging.info(f"IP {request.client.host} Attempted to connect but was Unauthorized")
    # A Basic web page with the entire purpose of redirecting the user away from the page.
    if "/api/" in request.url.path:
        return HTMLResponse("401: Forbidden", 401)
    return shared_templates.TemplateResponse(
        request,
        "401.html",
        status_code=401
    )

modules_dir = "website/modules"
disabled_modules = []
loaded_routers = set()
mounted_statics = set()
checked_route_modules = set()
loaded_middlewares = set()

for root, dirs, files in os.walk(modules_dir):
    rel_path = os.path.relpath(root, modules_dir)
    if rel_path == ".":
        continue

    module_parts = rel_path.split(os.sep)
    top_level_module = module_parts[0]

    if top_level_module in disabled_modules:
        logging.info(f"[!] Skipping disabled module: {top_level_module}")
        dirs[:] = []
        continue

    if "__pycache__" in module_parts:
        continue

    # Static Mounting
    static_path = os.path.join(root, "static")
    if os.path.isdir(static_path):
        mount_key = rel_path.replace(os.sep, "/")
        if mount_key not in mounted_statics:
            mount_path = f"/static/{mount_key}"
            fastapp.mount(
                mount_path,
                StaticFiles(directory=static_path),
                name=f"{mount_key}_static"
            )
            mounted_statics.add(mount_key)
            logging.info(f"[✓] Mounted static files for {mount_key} at {mount_path}")

    # Middleware Handling
    if top_level_module == "middleware" and "middleware.py" in files:
        module_import_path = "website.modules." + ".".join(module_parts) + ".middleware"

        if module_import_path not in loaded_middlewares:
            try:
                module = importlib.import_module(module_import_path)

                if hasattr(module, "middleware"):
                    fastapp.middleware("http")(module.middleware)
                    loaded_middlewares.add(module_import_path)
                    logging.info(f"[✓] Loaded middleware from {module_import_path}")
                else:
                    logging.info(f"[!] No 'middleware' callable in {module_import_path}")

            except Exception as err:
                logging.error(
                    f"[✗] Failed to load middleware {module_import_path}: {err}",
                    exc_info=err
                )

        continue  # don't also try to treat middleware as router

    # Router Handling
    if "routes.py" in files:
        module_import_path = "website.modules." + ".".join(module_parts) + ".routes"

        if module_import_path in checked_route_modules:
            continue

        checked_route_modules.add(module_import_path)

        try:
            module = importlib.import_module(module_import_path)
            if hasattr(module, "router"):
                fastapp.include_router(module.router)
                loaded_routers.add(module_import_path)
                logging.info(f"[✓] Loaded router from {module_import_path}")
            else:
                logging.info(f"[!] No 'router' found in {module_import_path}")
        except Exception as err:
            logging.error(
                f"[✗] Failed to load {module_import_path}: {err}",
                exc_info=err
            )

if __name__ == "__main__":
    # Initialize the database connection and create tables if they don't exist
    db_okay = db.initialize()
    if db_okay:
        db.modernize()
    else:
        print(f"Error: Unable to initialize the database connection. Please check your settings and ensure the database is reachable.")
        raise ConnectionError("Database initialization failed.")

    config = uvicorn.Config(
        fastapp,
        host="0.0.0.0",
        port=WEB_PORT,
        loop="asyncio",
        lifespan="on",
        reload=False,
    )
    server = uvicorn.Server(config)

    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("Shutdown signal detected, ending process.")
        sys.exit(0)
