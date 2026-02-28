from library.database.db_automod import nsfw_scanner_reviews, nsfw_scanner
import lightbulb

loader = lightbulb.Loader()

vote_threshold = 1

async def handle_task(for_upvote:bool):
    if for_upvote:
        # Only real change is this one handles upvoted images
        all_messages = nsfw_scanner_reviews.list_review_msgs(min_upvotes=vote_threshold)
        
        for msg in all_messages:
            if msg['upvotes'] > msg['downvotes']:
                nsfw_scanner.whitelist_image(msg['img_hash'])
            else:
                nsfw_scanner.blacklist_image(msg['img_hash'])
    else:
        all_messages = nsfw_scanner_reviews.list_review_msgs(min_downvotes=vote_threshold)
        
        for msg in all_messages:
            if msg['downvotes'] > msg['upvotes']:
                nsfw_scanner.whitelist_image(msg['img_hash'])
            else:
                nsfw_scanner.blacklist_image(msg['img_hash'])

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def upvote_task() -> None:
    await handle_task(True)

@loader.task(lightbulb.uniformtrigger(seconds=10, wait_first=False))
async def downvote_task() -> None:
    await handle_task(False)