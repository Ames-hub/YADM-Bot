from library.database.reaction_roles import rr_group, get_is_grouped_by_msg, rr_errors
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildReactionAddEvent)
async def botfunction(event: hikari.GuildReactionAddEvent):
    if event.member.is_bot:
        return

    group_id = get_is_grouped_by_msg(event.message_id, True)

    try:
        rrg = rr_group(group_id)
    except rr_errors.UngroupedMessage:
        return False
    
    is_custom = event.emoji_id != None
    
    await rrg.give_member_role(event.user_id, emoji=event.emoji_name if not is_custom else event.emoji_id)

@loader.listener(hikari.GuildReactionDeleteEvent)
async def botfunction(event: hikari.GuildReactionDeleteEvent):
    group_id = get_is_grouped_by_msg(event.message_id, True)

    try:
        rrg = rr_group(group_id)
    except rr_errors.UngroupedMessage:
        return False
    
    is_custom = event.emoji_id != None

    await rrg.take_member_role(event.user_id, emoji=event.emoji_name if not is_custom else event.emoji_id)