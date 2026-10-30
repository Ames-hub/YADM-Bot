from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return
    if not ds.d["channel_users_talking"].get(event.channel_id):
        ds.d["channel_users_talking"][event.channel_id] = {}
    ds.d["channel_users_talking"][event.channel_id][event.author.id] = event.author.display_name
    ds.d["all_users_talking"][event.author.id] = event.author.display_name