from library.database.db_automod import nsfw_scanner_reviews
from library import datastore as ds
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()
primary_maintainer = get.primary_maintainer()

@loader.listener(hikari.GuildReactionAddEvent)
async def botfunction(event: hikari.GuildReactionAddEvent):
    if event.user_id == ds.d["myid"]:
        return
    if not nsfw_scanner_reviews.is_tracked_msg(event.message_id):
        return

    amount = 1
    if event.user_id == primary_maintainer:
        amount + 99  # The primary maintainer's opinion over-rides other user's.
    
    if event.emoji_name == "👍":
        nsfw_scanner_reviews.modify_upvote_count(event.message_id, add=True, amount=amount)
    elif event.emoji_name == "👎":
        nsfw_scanner_reviews.modify_downvote_count(event.message_id, add=True, amount=amount)
    return True

@loader.listener(hikari.GuildReactionDeleteEvent)
async def botfunction(event: hikari.GuildReactionDeleteEvent):
    if event.user_id == ds.d["myid"]:
        return
    if not nsfw_scanner_reviews.is_tracked_msg(event.message_id):
        return

    amount = 1
    if event.user_id == primary_maintainer:
        amount + 99  # The primary maintainer's opinion over-rides other user's.
    
    if event.emoji_name == "👍":
        nsfw_scanner_reviews.modify_upvote_count(event.message_id, add=False, amount=amount)
    elif event.emoji_name == "👎":
        nsfw_scanner_reviews.modify_downvote_count(event.message_id, add=False, amount=amount)
    return True