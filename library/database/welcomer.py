from library.database.manage import get_session, guild_welcomer_enabled, guild_welcome_msg
from sqlalchemy.exc import SQLAlchemyError
import datetime
import logging
import hikari

class welcomer:
    def __init__(self, guild_id:int):
        self.guild_id = guild_id

    def set_enabled(self, value:bool):
        session = get_session()
        try:
            record = (
                session.query(guild_welcomer_enabled)
                .filter(guild_welcomer_enabled.guild_id == self.guild_id)
                .one_or_none()
            )

            if record:
                # Update existing record
                record.enabled = bool(value)
            else:
                # Insert new record
                record = guild_welcomer_enabled(
                    guild_id=self.guild_id,
                    enabled = bool(value)
                )
                session.add(record)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error(
                "Error updating or inserting welcomer online status!",
                exc_info=err
            )
            session.rollback()
            return False
        finally:
            session.close()

    def is_enabled(self):
        session = get_session()
        try:
            record = (
                session.query(guild_welcomer_enabled.enabled)
                .filter(guild_welcomer_enabled.guild_id == self.guild_id)
                .one_or_none()
            )
            return record is not None
        except SQLAlchemyError as err:
            logging.error("Error getting if the guild welcomer is enabled", exc_info=err)
            return False
        finally:
            session.close()

    def set_message(self, value:str):
        session = get_session()
        try:
            record = (
                session.query(guild_welcome_msg)
                .filter(guild_welcome_msg.guild_id == self.guild_id)
                .one_or_none()
            )

            if record:
                # Update existing record
                record.message = str(value)
            else:
                # Insert new record
                record = guild_welcome_msg(
                    guild_id=self.guild_id,
                    message=str(value)
                )
                session.add(record)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error(
                "Error updating or inserting welcomer's message!",
                exc_info=err
            )
            session.rollback()
            return False
        finally:
            session.close()

    def get_welcome_msg(self):
        session = get_session()
        try:
            message = (
                session.query(guild_welcome_msg.message)
                .filter(guild_welcome_msg.guild_id == self.guild_id)
                .one_or_none()
            )
            return message
        except SQLAlchemyError as err:
            logging.error("Error getting the guild welcomer msg", exc_info=err)
            return False
        finally:
            session.close()

    def gen_welcome_msg(self, user: hikari.Member):
        placeholders = {
            "<user_id>": str(user.id),
            "<timestamp>": str(datetime.datetime.now().timestamp()),
            "<display_name>": user.display_name,
            "<username>": user.username,
            "<mention>": user.mention
        }

        message = self.get_welcome_msg()

        for placeholder in placeholders.keys():
            message: str = message.replace(placeholder, placeholders[placeholder])

        return message