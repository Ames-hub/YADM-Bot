from library.permissions import perms
from library.botapp import botapp
from library.settings import get
import traceback
import lightbulb
import datetime
import logging
import hikari
import io

loader = lightbulb.Loader()

@loader.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    handled = False

    original_exception = exc.causes[0]  # What set it all off
    if isinstance(original_exception, perms.errors.user_perm_error):
        handled = True

    if not handled:
        await exc.context.respond("An error occurred while executing the command.")

        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)

        logging.error("I encountered an error!", exc_info=exc)
        PRIMARY_MAINTAINER_ID = get.primary_maintainer()

        if PRIMARY_MAINTAINER_ID:
            # Forms an attachment with the traceback using bytesIO library
            data = io.BytesIO("".join(tb).encode("utf-8"))
            attachment = hikari.Bytes(
                data,
                "error_traceback.txt",
            )

            dmc = await botapp.rest.create_dm_channel(PRIMARY_MAINTAINER_ID)
            await dmc.send(
                hikari.Embed(
                    title=f"Error!  :(",
                    timestamp=datetime.datetime.now().astimezone(),
                    color=0xff0000
                )
                .set_author(
                    name=exc.context.user.username,
                    icon=exc.context.user.default_avatar_url,
                )
                .add_field(
                    name="CONTEXT",
                    value=f"The user encountered the error \n\"{exc}\" at the posted timestamp. A full traceback is attached.\n\n"
                        f"Invoker: {exc.context.user.id} ({exc.context.user.username})\n"
                        f"In a Guild?: {exc.context.guild_id != None}\n"
                        f"Guild ID: {exc.context.guild_id}\n"
                        f"Is this bot an official instance?: {botapp.get_me().id in [1387493386575020164, 1090899298650169385]}\n"
                ),
                attachment=attachment
            )
            
            return True
        
    return handled