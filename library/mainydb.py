from MainyDB import MainyDB

# Create or open a database file
db = MainyDB("automod-imgs.mdb")
images_collection = db.automod.filtered_imgs

def archive_img(violation_id: int, img_bytes: bytes):
    result = images_collection.insert_one({
        "violation_id": violation_id,
        "data": img_bytes
    })
    return result

def get_img(violation_id: int) -> bytes:
    stored = images_collection.find_one({"violation_id": violation_id})
    try:
        retrieved_image_bytes = stored["data"]  # This is already decoded bytes
    except TypeError:
        return None  # No img saved
    return retrieved_image_bytes