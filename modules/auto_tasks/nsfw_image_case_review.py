from library.database.db_automod import nsfw_scanner_reviews, nsfw_scanner
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

vote_threshold = 1

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def task() -> None:
    all_messages = nsfw_scanner_reviews.list_review_msgs(min_downvotes=vote_threshold)
    
    for msg in all_messages:
        if msg['downvotes'] > msg['upvotes']:
            nsfw_scanner.whitelist_image(msg['img_hash'])
        else:
            nsfw_scanner.blacklist_image(msg['img_hash'])

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def task() -> None:
    # Only real change is this one handles upvoted images
    all_messages = nsfw_scanner_reviews.list_review_msgs(min_upvotes=vote_threshold)
    
    for msg in all_messages:
        if msg['upvotes'] > msg['downvotes']:
            nsfw_scanner.whitelist_image(msg['img_hash'])
        else:
            nsfw_scanner.blacklist_image(msg['img_hash'])