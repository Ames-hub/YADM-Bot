from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if ds.d.get(event.author.id, None) is None:
        ds.d[event.author.id] = event.author.display_name