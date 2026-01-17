from library.database.manage import get_session, automod_nsfw_scan_feedback, scanned_image_list
from sqlalchemy.exc import SQLAlchemyError
import logging


class nsfw_scanner_reviews:
    def is_tracked_msg(msg_id: int):
        session = get_session()
        try:
            record = (
                session.query(automod_nsfw_scan_feedback)
                .filter(automod_nsfw_scan_feedback.msg_id == msg_id)
                .one_or_none()
            )
            return record is not None
        except SQLAlchemyError as err:
            logging.error("Error checking if msg is tracked", exc_info=err)
            return False
        finally:
            session.close()

    def track_msg(msg_id:int, img_hash:str):
        session = get_session()
        try:
            record = automod_nsfw_scan_feedback(
                msg_id=msg_id,
                upvote_count=0,
                downvote_count=0,
                related_img_hash=img_hash
            )
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error adding msg to db to be tracked!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def modify_upvote_count(msg_id:int, add:bool=True):
        session = get_session()
        try:
            record = (
                session.query(automod_nsfw_scan_feedback)
                .filter(automod_nsfw_scan_feedback.msg_id == msg_id)
                .one_or_none()
            )

            if not record:
                return True

            if add:
                new_upvote_count = record.upvote_count + 1
            else:
                new_upvote_count = record.upvote_count - 1

            if not record:
                raise nsfw_scanner_reviews.errors.msg_not_tracked
            else:
                setattr(record, "upvote_count", new_upvote_count)

            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def modify_downvote_count(msg_id, add:bool=True):
        session = get_session()
        try:
            record = (
                session.query(automod_nsfw_scan_feedback)
                .filter(automod_nsfw_scan_feedback.msg_id == msg_id)
                .one_or_none()
            )

            if add:
                new_downvote_count = record.downvote_count + 1
            else:
                new_downvote_count = record.downvote_count - 1

            if not record:
                raise nsfw_scanner_reviews.errors.msg_not_tracked
            else:
                setattr(record, "downvote_count", new_downvote_count)

            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def list_review_msgs(min_upvotes=None, min_downvotes=None):
        session = get_session()
        try:
            if not min_upvotes and not min_downvotes:
                records = (
                    session.query(automod_nsfw_scan_feedback)
                    .all()
                )
            elif min_upvotes:
                records = (
                    session.query(automod_nsfw_scan_feedback)
                    .filter(
                        automod_nsfw_scan_feedback.upvote_count >= min_upvotes
                    )
                    .all()
                )
            elif min_downvotes:
                records = (
                    session.query(automod_nsfw_scan_feedback)
                    .filter(
                        automod_nsfw_scan_feedback.downvote_count >= min_downvotes
                    )
                    .all()
                )
            elif min_upvotes and min_upvotes:
                records = (
                    session.query(automod_nsfw_scan_feedback)
                    .filter(
                        automod_nsfw_scan_feedback.upvote_count >= min_upvotes,
                        automod_nsfw_scan_feedback.downvote_count >= min_downvotes
                    )
                    .all()
                )
            else:
                raise ValueError("Couldn't figure out what to grab") 

            parsed_data = []
            for item in records:
                parsed_data.append({
                    "msg_id": item.msg_id,
                    "upvotes": item.upvote_count,
                    "downvotes": item.downvote_count,
                    "img_hash": item.related_img_hash
                })
            return parsed_data
        except SQLAlchemyError:
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

    class errors:
        class msg_not_tracked(Exception):
            def __init__(self):
                pass

class nsfw_scanner:
    @staticmethod
    def _upsert_image(image_hash: str, whitelisted: bool):
        session = get_session()
        try:
            record = (
                session.query(scanned_image_list)
                .filter(scanned_image_list.image_hash == image_hash)
                .one_or_none()
            )

            if record:
                # Update existing record
                record.whitelisted = whitelisted
            else:
                # Insert new record
                record = scanned_image_list(
                    image_hash=image_hash,
                    whitelisted=whitelisted
                )
                session.add(record)

            session.commit()
            return True

        except SQLAlchemyError as err:
            logging.error(
                "Error updating or inserting image whitelist status!",
                exc_info=err
            )
            session.rollback()
            return False

        finally:
            session.close()

    @staticmethod
    def whitelist_image(image_hash: str):
        return nsfw_scanner._upsert_image(image_hash, True)

    @staticmethod
    def blacklist_image(image_hash: str):
        return nsfw_scanner._upsert_image(image_hash, False)
    
    @staticmethod
    def check_whitelisted(image_hash: str):
        session = get_session()
        try:
            record = (
                session.query(scanned_image_list.whitelisted)
                .filter(
                    scanned_image_list.image_hash == image_hash
                )
                .one_or_none()
            )

            if record:
                return record[0]
            else:
                return -1
        except SQLAlchemyError:
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()