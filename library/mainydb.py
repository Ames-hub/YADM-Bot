from MainyDB import MainyDB

# Create or open a database file
db = MainyDB("automod-imgs.mdb")
nsfw_images_collection = db.automod.filtered_imgs

class nsfw_scanner:
    def archive_img(violation_id: int, img_bytes: bytes):
        result = nsfw_images_collection.insert_one({
            "violation_id": violation_id,
            "data": img_bytes
        })
        return result

    def get_img(violation_id: int) -> bytes:
        stored = nsfw_images_collection.find_one({"violation_id": violation_id})
        try:
            retrieved_image_bytes = stored["data"]  # This is already decoded bytes
        except TypeError:
            return None  # No img saved
        return retrieved_image_bytes

guild_icons_collection = db.guilds.icons

class guild_icons:
    def archive_img(guild_id: int, img_bytes: bytes):
        result = guild_icons_collection.insert_one({
            "guild_id": guild_id,
            "data": img_bytes
        })
        return result

    def get_img(guild_id: int) -> bytes:
        stored = guild_icons_collection.find_one({"guild_id": guild_id})
        try:
            retrieved_image_bytes = stored["data"]  # This is already decoded bytes
        except TypeError:
            return None  # No img saved
        return retrieved_image_bytes