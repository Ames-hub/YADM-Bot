from library.database.manage import get_session, guild_honeypot
from library.database.auditing import server_logs
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
from library import datastore as ds
from library.botapp import botapp
import logging
import hikari

def gen_del_text(del_success:bool, mute_success:bool):
    if del_success:
        del_text = "and all messages younger than 1 hour have been deleted."
    else:
        if mute_success:
            del_text = "but we couldn't delete any messages."
        else:
            del_text = "and we couldn't delete any messages."
    return del_text

class honeypot:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    class errors:
        class honeypot_disabled(Exception):
            def __init__(self, *args):
                super().__init__(*args)

    def get_channel(self):
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    return None
                return record.channel_id
            except OperationalError as err:
                logging.error("Error getting honeypot channel for server", exc_info=err)
                session.rollback()
                return False

    def get_enabled(self) -> bool:
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    return False
                return record.enabled
            except OperationalError as err:
                logging.error("Error getting honeypot enabled status for server", exc_info=err)
                session.rollback()
                return False

    def get_do_ban(self) -> bool:
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    return True
                return record.do_ban
            except OperationalError as err:
                logging.error("Error getting honeypot do ban status for server", exc_info=err)
                session.rollback()
                return False

    def set_channel(self, channel_id:int) -> bool:
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    record = guild_honeypot(
                        guild_id=self.guild_id,
                        channel_id=channel_id,
                        enabled=True
                    )
                    session.add(record)
                    session.commit()
                    return True
                record.channel_id = channel_id
                session.commit()
                return True
            except OperationalError as err:
                logging.error("Error setting honeypot channel for server", exc_info=err)
                session.rollback()
                return False
            
    def set_enabled(self, value:bool) -> bool:
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    record = guild_honeypot(
                        guild_id=self.guild_id,
                        channel_id=None,
                        enabled=value
                    )
                    session.add(record)
                    session.commit()
                    return True
                record.enabled = value
                session.commit()
                return True
            except OperationalError as err:
                logging.error("Error setting honeypot enabled status for server", exc_info=err)
                session.rollback()
                return False

    def set_do_ban(self, do_ban:bool) -> bool:
        with get_session() as session:
            try:
                record = session.query(guild_honeypot).filter(guild_honeypot.guild_id == self.guild_id).one_or_none()
                if not record:
                    record = guild_honeypot(
                        guild_id=self.guild_id,
                        channel_id=None,
                        enabled=True,
                        do_ban=do_ban
                    )
                    session.add(record)
                    session.commit()
                    return True
                record.do_ban = do_ban
                session.commit()
                return True
            except OperationalError as err:
                logging.error("Error setting honeypot do ban status for server", exc_info=err)
                session.rollback()
                return False

    async def send_warning(self) -> bool:
        channel_id = self.get_channel()
        if not channel_id:
            return False

        text = "permanently banned." if self.get_do_ban() else "permanently muted."
        embed = (
            hikari.Embed(
                title="⚠️ No Messages! ⚠️",
                description=f"This is a honey-pot for spam bots! If you send a message in this channel, you'll be {text}",
                colour=0xffff00
            )
        )

        try:
            await botapp.rest.create_message(
                channel_id,
                embed,
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
            return False

    async def create(self, name:str="honey", send_warning:bool=False) -> bool:
        # make the channel
        try:
            channel = await botapp.rest.create_guild_text_channel(
                self.guild_id,
                name=name,
                position=0,
                nsfw=False,
                category=None,
                reason="User requested to make a honeypot channel.",
                topic="Do not talk in this channel!"
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
            return False

        if send_warning:
            await self.send_warning()
        
        self.set_channel(channel.id)
        return True

    async def setup(self, name:str="honey"):
        # Create the channel and set it
        success = await self.create(name)
        if not success:
            return False

        # Create the warning message
        success = await self.send_warning()
        if not success:
            return False
        
        # Enable the honeypot
        success = self.set_enabled(True)
        if not success:
            return False

        return True

    # TODO: Make it isolate muted honey-pot users.
    async def handle_honeypot_mute(self, user_id:int) -> tuple[bool, bool]:
        channel_id = self.get_channel()
        from library.database.guilds import muting  # Here to prevent circular imports.
        guildmute = muting.guilds(self.guild_id)
        mute_success = await guildmute.mute_member(
            user_id=user_id,
            reason="A message was sent in the honey-pot channel by this user.",
            moderator_id=ds.d["myid"],
            duration_s=-1,
            hardmute=True,
        )

        del_success = True
        try:
            messages = await botapp.rest.fetch_messages(
                channel_id,
                after=datetime.now() - timedelta(hours=1),
            )
            await botapp.rest.delete_messages(
                channel_id,
                messages
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
            del_success = False

        del_text = gen_del_text(del_success, mute_success)

        logs = server_logs(self.guild_id)

        if mute_success:
            await logs.create_entry(
                hikari.Embed(
                    title="Honeypot Tripped 🍯",
                    description=(
                        f"A message was sent in the honey-pot channel by <@{user_id}>,"
                        f" *this user has been permanently muted* {del_text}"
                    ),
                    colour=0xffff00
                )
            )
        else:
            await logs.create_entry(
                hikari.Embed(
                    title="Honeypot Tripped 🍯",
                    description=(
                        f"A message was sent in the honey-pot channel by <@{user_id}>,"
                        f" *we failed to mute this user* {del_text}"
                    ),
                    colour=0xffff00
                )
            )

        return (del_success, mute_success)

    async def handle_honeypot_ban(self, user_id:int):
        logs = server_logs(self.guild_id)
        try:
            await botapp.rest.ban_member(
                self.guild_id,
                user_id,
                delete_message_seconds=3600,
                reason="User tripped the anti spam-bot honeypot, and the guild has it configured to ban users who do this."
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError):
            # If we can't ban them, mute them.
            result = self.handle_honeypot_mute(user_id)
            del_success = result[0]
            mute_success = result[1]

            del_text = gen_del_text(del_success, mute_success)

            if mute_success:
                await logs.create_entry(
                    hikari.Embed(
                        title="Honeypot Tripped 🍯",
                        description=(
                            f"A message was sent in the honey-pot channel by <@{user_id}>, "
                            f"We don't have permissions to ban this user, so we muted them instead {del_text}"
                        ),
                        colour=0xff0000
                    )
                )
                return False
            else:
                await logs.create_entry(
                    hikari.Embed(
                        title="Honeypot Tripped 🍯",
                        description=(
                            f"A message was sent in the honey-pot channel by <@{user_id}>, "
                            f"We don't have permissions to ban this user, and we couldn't mute muted them {del_text}"
                        ),
                        colour=0xff0000
                    )
                )
                return False
        
        await logs.create_entry(
            hikari.Embed(
                title="Honeypot Tripped 🍯",
                description=(
                    f"A message was sent in the honey-pot channel by <@{user_id}>, "
                    "*this user has been banned* and all messages younger than 1 hour have been deleted."
                ),
                colour=0xffff00
            )
        )
        return True

    async def handle_tripped(self, user_id:int) -> bool:
        enabled = self.get_enabled()
        if not enabled:
            raise self.errors.honeypot_disabled

        do_ban = self.get_do_ban()
        if do_ban:
            success = await self.handle_honeypot_ban(user_id)
            return success
        else:
            result = await self.handle_honeypot_mute(user_id)
            del_success = result[0]
            mute_success = result[1]

            return del_success is True and mute_success is True