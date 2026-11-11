from library.database.guilds import dbguild
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageDeleteEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    # You get more points for every 50 characters in the message
    # Gets how many times the text content len goes into 50, then multiplies by 5.
    # Always returns 5 at minimum.
    exp_earned = max((len(event.message.content) // 50) * 5, 5)

    guild = dbguild(event.guild_id)
    result = guild.leveling.give_exp(
        user_id=event.author.id,
        exp=exp_earned,
        check_level=True
    )

    if result['lvl_is_diff']:
        old_lvl = result['old_lvl']
        new_lvl = result['new_lvl']
        if new_lvl > old_lvl:
            embed = hikari.Embed(
                title="Level Up! ✨",
                description=f"Congratulations {event.author.mention}, you just levelled up to level {new_lvl}!",
                colour=0xFFD700
            )
            guild_perk = guild.leveling.get_guild_level_perk(new_lvl)
            if guild_perk is not None:
                embed.add_field(
                    name="New Perks!",
                    value=f"You've unlocked the perks that come with the role <@&{guild_perk.role_id}>"
                )

            channel = guild.leveling.get_dedicated_channel()
            if channel is not None:
                await botapp.rest.create_message(
                    channel,
                    embed
                )
            else:
                await event.message.respond(embed)