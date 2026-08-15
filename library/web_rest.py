"""
Standalone Discord REST client for use in the website process (webui.py).

Unlike `library.botapp.botapp`, this does NOT open a gateway connection.
It's a bare `hikari.RESTApp()`, safe to use in a process that never
connects to Discord's gateway - which is what webui.py is, since it runs
separately from bot.py.

This exists because we need to check permissions on the website. So, yes :D

Usage:
    On FastAPI startup: await web_rest.start()
    On FastAPI shutdown: await web_rest.stop()
    In request handlers: web_rest.get_rest()
"""
from library.settings import get
import hikari

_rest_app = hikari.RESTApp()
_rest_client = None


async def start():
    """Call once, when webui.py boots up."""
    global _rest_client
    await _rest_app.start()
    _rest_client = _rest_app.acquire(get.appropriate_bot_token(), hikari.TokenType.BOT)
    await _rest_client.__aenter__()


async def stop():
    """Call once, when webui.py shuts down."""
    global _rest_client
    if _rest_client is not None:
        await _rest_client.__aexit__(None, None, None)
        _rest_client = None
    await _rest_app.close()


def get_rest():
    """Returns the started REST client. Raises if start() hasn't run yet."""
    if _rest_client is None:
        raise RuntimeError("web_rest.start() has not been called yet - is webui.py's lifespan set up?")
    return _rest_client