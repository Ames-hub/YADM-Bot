from library.database.leveling import user_activity, guild_leveling
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.MessageCreateEvent)
async def botfunction(event: hikari.MessageCreateEvent):
    if not event.author.id == get.primary_maintainer():
        return

    if event.message.content == "--convert-activity-to-exp":
        msg_count_list = user_activity.count_all_messages()
        for guild_id in msg_count_list:
            
            guild = msg_count_list[guild_id]
            leveling = guild_leveling(guild_id)

            for user_id, msg_count in guild.items():
                leveling.give_exp(user_id, 5 * msg_count)

        await event.message.respond(
            hikari.Embed(
                title="EXP Given retroactively",
                description=f"All EXP has been given retroactively for activity to all users.",
                colour=0x0000ff
            )
        )