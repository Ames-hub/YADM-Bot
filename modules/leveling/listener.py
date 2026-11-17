from library.shared import calc_exp_earned, is_user_spamming
from library.database.observations import get_entry
from library.database.guilds import dbguild
from library.botapp import botapp
from cachetools import TTLCache
import lightbulb
import hikari

loader = lightbulb.Loader()

users_cooldown = TTLCache(500, ttl=5)
spam_cooldown = TTLCache(500, ttl=300)

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    # Wait 5 seconds before they can earn EXP again.
    if users_cooldown.get(event.author.id, False):
        return

    users_cooldown[event.author.id] = True

    is_spamming = is_user_spamming(event.guild_id, event.author.id)
    if is_spamming or spam_cooldown.get(event.author.id, False):
        spam_cooldown[event.author.id] = True
        return  # Ignore them for 5 minutes

    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    exp_earned = calc_exp_earned(len(event.message.content))

    result = guild.leveling.give_exp(
        user_id=event.author.id,
        exp=exp_earned,
        check_level=True
    )

    if result['lvl_is_diff']:
        old_lvl = result['old_lvl']
        new_lvl = result['new_lvl']
        await guild.leveling.handle_level_up(
            target_user_id=event.author_id,
            send_to_channel_id=event.channel_id,
            old_lvl=old_lvl,
            new_lvl=new_lvl
        )

@loader.listener(hikari.GuildMessageDeleteEvent)
async def botfunction(event: hikari.GuildMessageDeleteEvent):
    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    entry = get_entry(int(event.message_id))
    if entry is None:
        return
    
    exp_lost = calc_exp_earned(len(entry.msg_content))

    result = guild.leveling.remove_exp(
        user_id=entry.user_id,
        exp=exp_lost,
        check_level=True
    )

    if result['lvl_is_diff']:
        old_lvl = result['old_lvl']
        new_lvl = result['new_lvl']

        channel_id = guild.leveling.get_dedicated_channel()
        if not channel_id:
            channel_id = entry.channel_id  # where the message was sent. It may not exist anymore.

        embed = (
            hikari.Embed(
                title="Level Down!",
                description=f"<@{entry.user_id}> Just lost some EXP, causing them to lose a level!",
                colour=0xff0000
            )
            .set_footer(
                text=f"Lvl {old_lvl} -> lvl {new_lvl}"
            )
        )

        try:
            await botapp.rest.create_message(
                channel_id,
                embed
            )
        except (hikari.NotFoundError, hikari.ForbiddenError, hikari.BadRequestError):
            pass

@loader.listener(hikari.GuildBulkMessageDeleteEvent)
async def botfunction(event: hikari.GuildBulkMessageDeleteEvent):
    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    for msg_id in event.message_ids:
        entry = get_entry(int(msg_id))
        if not entry:
            continue

        exp_lost = calc_exp_earned(len(entry.msg_content))
        result = guild.leveling.remove_exp(
            user_id=entry.user_id,
            exp=exp_lost,
            check_level=True
        )

        if result['lvl_is_diff']:
            old_lvl = result['old_lvl']
            new_lvl = result['new_lvl']

            embed = (
                hikari.Embed(
                    title="Level Down!",
                    description=f"<@{entry.user_id}> Just lost some EXP, causing them to lose a level!",
                    colour=0xff0000
                )
                .set_footer(
                    text=f"Lvl {old_lvl} -> lvl {new_lvl}"
                )
            )

            channel_id = guild.leveling.get_dedicated_channel()
            if not channel_id:
                channel_id = entry.channel_id  # where the message was sent. It may not exist anymore.

            try:
                await botapp.rest.create_message(
                    channel_id,
                    embed
                )
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.BadRequestError):
                pass