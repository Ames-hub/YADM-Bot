from library.database.manage import get_session, nsfw_img_blob, guild_icon_blob
from library.settings import get
from MainyDB import MainyDB

# Create or open a database file
db = MainyDB("automod-imgs.mdb")
nsfw_images_collection = db.automod.filtered_imgs

class nsfw_scanner:
    def archive_img(violation_id: int, img_bytes: bytes):
        if get.prefer_mainydb():
            result = nsfw_images_collection.insert_one({
                "violation_id": violation_id,
                "data": img_bytes
            })
            return result
        else:
            with get_session() as session:
                record = nsfw_img_blob(
                    violation_id=violation_id,
                    img_blob=img_bytes,
                )
                session.add(record)
                session.commit()
            return True

    def get_img(violation_id: int) -> bytes:
        if get.prefer_mainydb():
            stored = nsfw_images_collection.find_one({"violation_id": violation_id})
            try:
                retrieved_image_bytes = stored["data"]  # This is already decoded bytes
            except TypeError:
                return None  # No img saved
            return retrieved_image_bytes
        else:
            with get_session() as session:
                record = (
                    session.query(nsfw_img_blob)
                    .filter(nsfw_img_blob.violation_id == violation_id)
                    .one_or_none()
                )
            return record.img_blob

guild_icons_collection = db.guilds.icons

class guild_icons:
    @staticmethod
    def archive_img(guild_id: int, img_bytes: bytes):
        if guild_icons.get_img(guild_id) is not None:
            raise ValueError("Cannot archive twice for the same guild")

        if get.prefer_mainydb():
            result = guild_icons_collection.insert_one({
                "guild_id": guild_id,
                "data": img_bytes
            })
            return result
        else:
            with get_session() as session:
                record = guild_icon_blob(
                    guild_id=guild_id,
                    img_blob=img_bytes,
                )
                session.add(record)
                session.commit()
            return True            

    @staticmethod
    def destroy(guild_id:int):
        if get.prefer_mainydb():
            guild_icons_collection.delete_one({"guild_id": guild_id})
            return True
        else:
            with get_session() as session:
                record = (
                    session.query(guild_icon_blob)
                    .filter(guild_icon_blob.guild_id == guild_id)
                    .one_or_none()
                )
                if not record:
                    return False
                session.delete(record)
                session.commit()
            return True

    @staticmethod
    def get_img(guild_id: int) -> bytes:
        if get.prefer_mainydb():
            stored = guild_icons_collection.find_one({"guild_id": guild_id})
            if stored is None:
                return None
            retrieved_image_bytes = stored["data"]  # This is already decoded bytes
            return retrieved_image_bytes
        else:
            with get_session() as session:
                record = (
                    session.query(guild_icon_blob)
                    .filter(guild_icon_blob.guild_id == guild_id)
                    .one_or_none()
                )
                if not record:
                    return None
            return record.img_blob