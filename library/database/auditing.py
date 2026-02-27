from library.database.manage import get_session, guild_audit_log_entry, guild_log_channel
from sqlalchemy.exc import SQLAlchemyError
from library.botapp import botapp
import logging
import hikari

"""
This is a file used by the bot to keep logs for actions in each server up-to-date.
"""

class logs_config:
    def __init__(self, guild_id:int):
        self.guild_id = int(guild_id)

    def set_logs_channel(self, channel:int):
        session = get_session()
        try:
            record = (
                session.query(guild_log_channel)
                .filter(guild_log_channel.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_log_channel(
                    guild_id=self.guild_id,
                    channel=int(channel)
                )
                session.add(record)
            else:
                record.channel = int(channel)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating audit logs channel for a server!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def get_logs_channel(self):
        session = get_session()
        try:
            records = (
                session.query(guild_log_channel.channel)
                .filter(guild_log_channel.guild_id == self.guild_id)
                .all()
            )
            return records
        except SQLAlchemyError as err:
            logging.error("Error getting the logs channel!", exc_info=err)
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

class server_logs:
    def __init__(self, guild_id:int):
        self.guild_id = int(guild_id)
        self.entry_text = None
    
    def __archive_log(self, entry_text:str):
        session = get_session()
        try:
            record = guild_audit_log_entry(
                guild_id=self.guild_id,
                entry_text=entry_text
            )
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Encountered an error logging an audit logs archive to the DB!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    async def log(self, embed:hikari.Embed) -> bool:
        config = logs_config(self.guild_id)

        entry_text = f"{embed.title}\n{embed.description}"
        self.__archive_log(entry_text)

        if embed.color == None or embed.colour == None:
            raise ValueError("Colour for embed cannot be None!")

        try:
            await botapp.rest.create_message(
                config.get_logs_channel(),
                content=embed
            )
            return True
        except (hikari.UnauthorizedError, hikari.ForbiddenError):
            return False
        except hikari.NotFoundError:
            config.set_logs_channel(None)