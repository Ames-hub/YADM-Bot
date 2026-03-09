from library.other import get_os_name
from library.permissions import perms
from library.botapp import botapp
from library.settings import get
import traceback
import lightbulb
import datetime
import platform
import logging
import psutil
import hikari
import sys
import io
import re
import os

loader = lightbulb.Loader()
official_bot_id = 1461801438446616618

def find_user_code_file(exc):
    """Find the file where the real command error occurred."""

    tb = traceback.extract_tb(exc.__traceback__)

    for frame in reversed(tb):
        path = frame.filename

        # Skip installed libraries
        if "site-packages" in path:
            continue

        if os.path.exists(path):
            return path

    return None


def get_command_meta_from_exception(exc):
    """Extract command name, description, group, and file from the real command file."""

    file_path = find_user_code_file(exc)

    if not file_path:
        return {"command_name": "unknown", "description": "unknown", "group": None, "file": None}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return {"command_name": "unknown", "description": "unknown", "group": None, "file": file_path}

    loader_match = re.search(r"@loader\.command", content)
    group_match = re.search(r"@(\w+)\.register", content)

    if not loader_match and not group_match:
        return {"command_name": "not a command", "description": None, "group": None, "file": file_path}

    group_name = group_match.group(1) if group_match else None

    name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
    desc_match = re.search(r'description\s*=\s*"([^"]+)"', content)

    name = name_match.group(1) if name_match else "unknown"
    description = desc_match.group(1) if desc_match else "unknown"

    return {
        "command_name": name,
        "description": description,
        "group": group_name,
        "file": file_path
    }


def collect_context_info(ctx: lightbulb.Context, exc):
    options = None
    try:
        if ctx.options:
            options = ""
            for option in ctx.options:
                options += f"{option.name}: \"{option.value}\" ({option.type})"
        else:
            options = "No options were provided"
    except Exception:
        options = "Failed to parse options"

    command_meta = get_command_meta_from_exception(exc)

    return {
        "command": command_meta["command_name"],
        "description": command_meta["description"],
        "group": command_meta["group"],
        "file": command_meta["file"],
        "user_id": ctx.user.id,
        "username": ctx.user.username,
        "channel_id": ctx.channel_id,
        "guild_id": ctx.guild_id,
        "is_dm": ctx.guild_id is None,
        "options": options
    }


def collect_system_info():
    """Collect system and process diagnostics."""
    proc = psutil.Process(os.getpid())

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "os_name": get_os_name(),
        "cpu_count": os.cpu_count(),
        "pid": os.getpid(),
        "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 2),
        "threads": proc.num_threads(),
        "uptime": datetime.datetime.now() - datetime.datetime.fromtimestamp(proc.create_time()),
    }


def collect_bot_info():
    try:
        me = botapp.get_me()
    except Exception:
        me = None

    return {
        "bot_id": getattr(me, "id", "unknown"),
        "guild_count": len(botapp.cache.get_guilds_view()) if botapp.cache else "unknown",
        "latency_ms": round(botapp.heartbeat_latency * 1000, 2) if botapp.heartbeat_latency else "unknown",
    }


@loader.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    handled = False

    # Unwrap the original exception
    original_exception = exc.causes[0] if getattr(exc, "causes", None) else exc

    tb_frames = traceback.extract_tb(original_exception.__traceback__)
    if tb_frames:
        last_frame = tb_frames[-1]
        crash_file = last_frame.filename
        crash_line_number = last_frame.lineno
        crash_code = last_frame.line
    else:
        crash_file = crash_line_number = crash_code = "unknown"

    if isinstance(original_exception, perms.errors.user_perm_error):
        handled = True

    if handled:
        return True

    ctx = exc.context

    await ctx.respond(
        hikari.Embed(
            title="Error Handler",
            description=(
                "Sorry, but when you tried to run that command, we encountered an error.\n"
                "We were unable to recover from it, so the command has crashed. Please try to run the command again, and let us know if it fails again."
            ),
            colour=0xff0000
        )
        .add_field(
            name="What happened?",
            value=f"||In this command, we encountered a \"{original_exception}\" error.||"
        )
    )

    tb = traceback.format_exception(type(original_exception), original_exception, original_exception.__traceback__)

    logging.error("Unhandled command error", exc_info=original_exception)

    PRIMARY_MAINTAINER_ID = get.primary_maintainer()
    if not PRIMARY_MAINTAINER_ID:
        return False

    # Collect diagnostic info
    system_info = collect_system_info()
    context_info = collect_context_info(ctx, original_exception)
    bot_info = collect_bot_info()

    report_notb = f"""
===== ERROR REPORT =====
Timestamp: {datetime.datetime.now().astimezone()}

----- Exception -----
{original_exception}

----- Crash Location -----
File: {crash_file}
Line: {crash_line_number}
Problem Line:
```
{crash_code}
```

----- Context -----
Command: {context_info['command']}
Description: {context_info['description']}
Group: {context_info['group']}
File: {context_info['file']}
User: {context_info['username']} ({context_info['user_id']})
Channel: {context_info['channel_id']}
Guild: {context_info['guild_id']}
Is DM: {context_info['is_dm']}

Command Options:\n{context_info['options']}

----- Bot -----
Bot ID: {bot_info['bot_id']}
Is Official Instance: {bot_info['bot_id'] == official_bot_id}
Guild Count: {bot_info['guild_count']}
Latency: {bot_info['latency_ms']} ms

----- System -----
Platform: {system_info['platform']}
OS Name: {system_info['os_name']}
Python: {system_info['python']}
CPU Count: {system_info['cpu_count']}

----- Process -----
PID: {system_info['pid']}
Memory: {system_info['memory_mb']} MB
Threads: {system_info['threads']}
Uptime: {system_info['uptime']}
"""

    report_tb = report_notb + f"""
----- Traceback -----
{''.join(tb)}
"""

    data = io.BytesIO(report_tb.encode("utf-8"))

    attachment = hikari.Bytes(
        data,
        "error_report.txt"
    )

    try:
        dmc = await botapp.rest.create_dm_channel(PRIMARY_MAINTAINER_ID)

        embed = (
            hikari.Embed(
                title="🚨 Command Error",
                description=f"Command `{context_info['command']}` failed.",
                color=0xff0000,
                timestamp=datetime.datetime.now().astimezone()
            )
            .set_author(
                name=context_info["username"],
                icon=ctx.user.display_avatar_url,
            )
            .add_field(
                "User",
                f"{context_info['username']} ({context_info['user_id']})",
                inline=True
            )
            .add_field(
                "Guild",
                str(context_info["guild_id"]),
                inline=True
            )
            .add_field(
                "Channel",
                str(context_info["channel_id"]),
                inline=True
            )
            .add_field(
                "Full Report",
                report_notb
            )
        )

        await dmc.send(embed=embed, attachment=attachment)

    except Exception:
        logging.error("Failed to send error report DM.", exc_info=True)

    return True