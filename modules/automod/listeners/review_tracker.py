from library.database.db_automod import nsfw_scanner_reviews
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildReactionAddEvent)
async def botfunction(event: hikari.GuildReactionAddEvent):
    if not nsfw_scanner_reviews.is_tracked_msg(event.message_id):
        return
    
    if event.emoji_name == "👍":
        nsfw_scanner_reviews.modify_upvote_count(event.message_id, add=True)
    elif event.emoji_name == "👎":
        nsfw_scanner_reviews.modify_downvote_count(event.message_id, add=True)
    return True

@loader.listener(hikari.GuildReactionDeleteEvent)
async def botfunction(event: hikari.GuildReactionDeleteEvent):
    if not nsfw_scanner_reviews.is_tracked_msg(event.message_id):
        return
    
    if event.emoji_name == "👍":
        nsfw_scanner_reviews.modify_upvote_count(event.message_id, add=False)
    elif event.emoji_name == "👎":
        nsfw_scanner_reviews.modify_downvote_count(event.message_id, add=False)
    return True