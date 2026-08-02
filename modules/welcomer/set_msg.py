from library.database.auditing import server_logs
from library.database.welcomer import welcomer
from library.permissions import prechecks
from modules.welcomer.group import group
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_setmsg_command(guild_id:int, new_msg:str, responder_func):
    wc = welcomer(guild_id)

    success = wc.set_message(new_msg)
    if not success:
        await responder_func(
            hikari.Embed(
                title="Failed!",
                description="Couldn't set the message? This is a bug!",
                colour=0xff0000
            )
        )
        return

    embed = (
        hikari.Embed(
            title="Welcomer Message",
            description="The message has been set!",
            colour=0x00ff00
        )
    )

    await server_logs(guild_id).create_entry(
        hikari.Embed(
            title="Welcomer Message",
            description=f"On users joining, they will now be welcomed with the message:\n\"{new_msg}\"",
            colour=0x00ff00
        )
    )
    await responder_func(embed)

@group.register
class command(
    lightbulb.SlashCommand,
    name="message",
    description="Set what the welcomer says to new people!"
):

    text = lightbulb.string("message", "What do we say to welcome people?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("welcomer setmsg", ctx, hikari.Permissions.MANAGE_MESSAGES)
        return await handle_setmsg_command(ctx.guild_id, self.text, ctx.respond)