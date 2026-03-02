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

    async def mk_logs_channel(self):
        try:
            channel = await botapp.rest.create_guild_text_channel(
                self.guild_id,
                "nodeus-logs",
                reason="Creating audit logs channel for the server, as part of setting up recommended settings!"
            )
            await botapp.rest.edit_permission_overwrite(
                channel=channel.id,
                target_type=hikari.PermissionOverwriteType.ROLE,
                target=self.guild_id,
                deny=68608,  # Deny send messages, view channel, read history to all members
            )
            self.set_logs_channel(channel.id)
            return True
        except (hikari.UnauthorizedError, hikari.ForbiddenError):
            return False
        except hikari.NotFoundError:
            return False 

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
                .one_or_none()
            )
            return records[0] if records else None
        except SQLAlchemyError as err:
            logging.error("Error getting the logs channel!", exc_info=err)
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

class server_logs:
    def __init__(self, guild_id:int):
        self.guild_id = int(guild_id)
        self.entry_text = None
    
    class NoLogsChannel(Exception):
        def __init__(self, *args):
            super().__init__(*args)

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

    async def create_entry(self, embed:hikari.Embed, no_channel_ok:bool=True) -> bool:
        config = logs_config(self.guild_id)

        entry_text = f"{embed.title}\n{embed.description}"
        self.__archive_log(entry_text)

        if embed.color == None or embed.colour == None:
            raise ValueError("Colour for embed cannot be None!")

        logs_channel = config.get_logs_channel()
        if not logs_channel:
            if no_channel_ok:
                return True
            else:
                raise self.NoLogsChannel

        try:
            await botapp.rest.create_message(
                channel=logs_channel,
                content=embed
            )
            return True
        except (hikari.UnauthorizedError, hikari.ForbiddenError):
            return False
        except hikari.NotFoundError:
            config.set_logs_channel(None)