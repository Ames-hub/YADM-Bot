from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return
    
    message = event.message.content.strip().lower()

    guilty = automod.check(message)

    if guilty:
        await event.message.delete()
        await event.message.respond(
            hikari.Embed(
                title="Automod Action",
                description=f"{event.author.mention}, your message was found to violate the rules.\nIt has been deleted."
            )
        )