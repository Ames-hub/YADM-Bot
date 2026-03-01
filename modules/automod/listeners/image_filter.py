from library.database.db_automod import nsfw_scanner_reviews, nsfw_scanner
from library.database.guilds import dbguild
from library import datastore as ds
from library.botapp import botapp
from library import automod
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    if not event.message.attachments:
        return  # No attachments

    # if the admins have marked them as exempted, don't interact with them
    if event.author.id in ds.d["filter_exemptions"].get(int(event.guild_id), []):
        return

    guild = dbguild(event.guild_id)
    if not guild.get.do_image_filtering():
        return
    
    await event.message.add_reaction("🔍")

    try:
        for attached in event.message.attachments:
            image_bytes = await attached.read()
            
            result = automod.checks.ai_vision.predict_is_nsfw(image_bytes)
            guilty = result['nsfw']
            
            if guilty:
                break
    except automod.checks.ai_vision.ai_disabled:
        return

    if guilty:
        embed=(
            hikari.Embed(
                title=F"({result['probability']}) NSFW Image Detected 🔞",
                description=f"{event.author.mention} We have detected that this image violates content rules."
            )
            .set_footer("Did we get it right? If not, react to this message with 👎\nBut if this was an NSFW image, react with 👍")
        )

        msg_id = await automod.handle_guilty(event, alert_embed=embed, get_msg_id=True, automod_type=automod.automod_types.IMAGE_FILTER)
        
        img_hash = automod.generate_hash(image_bytes)
        nsfw_scanner_reviews.track_msg(msg_id=msg_id, img_hash=img_hash)
        nsfw_scanner.blacklist_image(
            image_hash=img_hash
        )

        # Remove the reaction if the msg isn't going to be deleted.
        if not guild.get.do_delete_msg():
            await event.message.remove_reaction("🔍", user=botapp.get_me().id)
        return True
    else:
        await event.message.remove_reaction("🔍", user=botapp.get_me().id)
        return True