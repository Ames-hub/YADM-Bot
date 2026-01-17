from library.database.manage import get_session, guild_automod_settings, member_violations, guild_custom_wordlist, mute_records, guild_member_warnings
from sqlalchemy.exc import SQLAlchemyError
from library.botapp import botapp
import datetime
import logging
import hikari

class muting:
    class guilds:
        def __init__(self, guild_id:int):
            self.guild_id = int(guild_id)

        async def mute_member(self, user_id:int, duration_s:int=600, hardmute:bool=False):
            """
            Mute a member in a guild for a specific amount of seconds.
            
            :param guild_id: Which guild it happens in
            :type guild_id: int
            :param user_id: The target to be muted
            :type user_id: int
            :param duration_s: How many seconds the mute should last.
            :type duration_s: int
            :param hardmute: Remove ALL other rolls from the individual except "muted". Vaguelly destructive.
            :type hardmute: bool
            """
            guild_id = self.guild_id
            user_id = int(user_id)

            muted_role = dbguild(guild_id).get.muted_role_id()
            if not muted_role:
                success = await self.create_muted_role()
                if not success:
                    return False
            
            if hardmute:
                try:
                    member = await botapp.rest.fetch_member(self.guild_id, user_id)
                    member_roles = member.get_roles()
                    for role in member_roles:
                        await botapp.rest.remove_role_from_member(
                            guild=guild_id,
                            user=user_id,
                            role=role.id
                        )
                except hikari.ForbiddenError:
                    # Insufficient permissions. Skip
                    logging.info(f"Guild {guild_id} Tried to hard-mute {user_id} but I didn't have permissions sufficient to do it.")
                    pass

            try:
                await botapp.rest.add_role_to_member(
                    guild=guild_id,
                    user=user_id,
                    role=muted_role
                )
            except hikari.ForbiddenError:
                return False

            # Make a record in the DB to say the person needs to be unmuted eventually
            session = get_session()
            try:
                record = mute_records(
                    user_id=user_id,
                    guild_id=guild_id,
                    scheduled_unmute=datetime.datetime.now().timestamp() + duration_s
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record.case_id
            except SQLAlchemyError:
                session.rollback()
                raise
            finally:
                session.close()

        async def create_muted_role(self):
            try:
                new_role = await botapp.rest.create_role(
                    guild=self.guild_id,
                    permissions=1115136,
                    colour=0xff0000,
                    hoist=True,  # HOIST OF SHAME >:(
                    mentionable=False,
                    reason="Guild did not have a pre-set muted role assigned for the bot.",
                    name="muted"
                )
            except hikari.ForbiddenError:
                return False

            guild = dbguild(self.guild_id)
            success = guild.set.muted_role_id(new_role.id)
            return success

    def list_all_mutes(active_only=True):
        session = get_session()
        try:
            if active_only:
                records = (
                    session.query(mute_records)
                    .filter(mute_records.active == True)
                    .all()
                )
            else:
                records = (
                    session.query(mute_records)
                    .all()
                )

            return {
                record.case_id: {
                    "user_id": record.user_id,
                    "guild_id": record.guild_id,
                    "scheduled_unmute": record.scheduled_unmute,
                }
                for record in records
            }
        finally:
            session.close()

    def set_mute_inactive(mute_id):
        session = get_session()
        try:
            record = (
                session.query(mute_records)
                .filter(mute_records.case_id == mute_id)
                .one_or_none()
            )

            if not record:
                raise muting.errors.mute_not_found
            else:
                setattr(record, "active", False)

            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()
    
    class errors:
        class mute_not_found(Exception):
            def __init__(self):
                pass

class violations:
    def create_member_violation(
        reporter_id: int,
        offender_id: int,
        time: datetime,
        violation: str,
        automated: bool
    ) -> int:

        reporter_id = int(reporter_id)
        offender_id = int(offender_id)
        if not isinstance(time, datetime.datetime): raise TypeError(f"The time is not a datetime! Got \"{time}\" ({type(time)})")
        violation = str(violation)
        automated = bool(automated)

        session = get_session()
        try:
            record = member_violations(
                reporter_id=reporter_id,
                offender_id=offender_id,
                time=time,
                violation=violation,
                automated=automated,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.entry_id
        except SQLAlchemyError as err:
            logging.error("Error adding member violation!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def get_violation_record(entry_id: int) -> member_violations | None:
        session = get_session()
        try:
            return (
                session.query(member_violations)
                .filter(member_violations.entry_id == entry_id)
                .one_or_none()
            )
        finally:
            session.close()

    def get_violations_by_offender(offender_id: int) -> list[member_violations]:
        session = get_session()
        try:
            return (
                session.query(member_violations)
                .filter(member_violations.offender_id == offender_id)
                .order_by(member_violations.time.desc())
                .all()
            )
        finally:
            session.close()

class automod_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _get_record(self):
        session = get_session()
        try:
            return (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
        finally:
            session.close()

    def get_text_filter_level(self):
        record = self._get_record()
        return record.text_filter_level if record else 1

    def do_delete_msg(self):
        record = self._get_record()
        return record.penalty_delete_message if record else False

    def do_warn_member(self):
        record = self._get_record()
        return record.penalty_warn_member if record else False

    def do_mute_member(self):
        record = self._get_record()
        return record.penalty_mute_member if record else False

    def get_mute_duration(self):
        record = self._get_record()
        return record.penalty_mute_duration if record else 60

    def do_kick_member(self):
        record = self._get_record()
        return record.penalty_kick_member if record else False

    def do_ban_member(self):
        record = self._get_record()
        return record.penalty_ban_member if record else False

    def get_ban_msg_purgetime(self):
        record = self._get_record()
        return record.ban_msg_purgetime if record else 600  # 10 minutes

    def muted_role_id(self):
        record = self._get_record()
        return record.muted_role_id if record else None

class automod_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_automod_settings(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def set_text_filter_level(self, level: int):
        return self._update(text_filter_level=level)

    def do_delete_msg(self, value: bool):
        return self._update(penalty_delete_message=value)

    def do_warn_member(self, value: bool):
        return self._update(penalty_warn_member=value)

    def do_mute_member(self, value: bool):
        return self._update(penalty_mute_member=value)

    def set_mute_duration(self, seconds: int):
        return self._update(penalty_mute_duration=seconds)

    def do_kick_member(self, value: bool):
        return self._update(penalty_kick_member=value)

    def do_ban_member(self, value: bool):
        return self._update(penalty_ban_member=value)

    def set_ban_msg_purgetime(self, value: int):
        return self._update(ban_msg_purgetime=value)

    def muted_role_id(self, value:int):
        return self._update(muted_role_id=value)

class wordlist_modify:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def add_word(self, word:str, blacklisted:bool):
        session = get_session()
        try:
            record = guild_custom_wordlist(
                guild_id=self.guild_id,
                word=word,
                blacklisted=blacklisted
            )
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Encountered an error in adding a word to the list!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def remove_word(self, word):
        session = get_session()
        try:
            record = (
                session.query(guild_custom_wordlist)
                .filter(
                    guild_custom_wordlist.guild_id == self.guild_id,
                    guild_custom_wordlist.word == word,
                )
                .one_or_none()
            )

            if not record:
                return False  # Nothing to delete

            session.delete(record)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def get_list(self, blacklist_only:bool=False, whitelist_only:bool=False):
        session = get_session()
        try:
            if blacklist_only:
                records = (
                    session.query(guild_custom_wordlist.word)
                    .filter(guild_custom_wordlist.guild_id == self.guild_id)
                    .filter(guild_custom_wordlist.blacklisted == True)
                    .all()
                )
            if whitelist_only and not blacklist_only:
                records = (
                    session.query(guild_custom_wordlist.word)
                    .filter(guild_custom_wordlist.guild_id == self.guild_id)
                    .filter(guild_custom_wordlist.blacklisted == False)
                    .all()
                )
            else:  # both false. Get all
                records = (
                    session.query(guild_custom_wordlist.word)
                    .filter(guild_custom_wordlist.guild_id == self.guild_id)
                    .all()
                )
            # `records` is a list of tuples, so we extract the first element from each tuple
            return [r[0] for r in records]
        except SQLAlchemyError:
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

class guild_warnings:
    def __init__(self, guild_id):
        self.guild_id = guild_id
    
    def add_warning(self, reason:str, mod_id:int, user_id:int):
        """
        Add a warning to someone's account. This is specific to a guild, and is different from a violation in that its not bot-wide.

        :param reason: Why they were warned
        :type reason: str
        :param mod_id: Who added the warning
        :type mod_id: int
        :param user_id: Who got warned
        :type user_id: int
        :param guild_id: Description
        :type guild_id: int
        """
        reason = str(reason)
        mod_id = int(mod_id)
        user_id = int(user_id)
        guild_id = int(self.guild_id)

        session = get_session()
        try:
            record = guild_member_warnings(
                reason=reason,
                moderator_id=mod_id,
                user_id=user_id,
                guild_id=guild_id,
                time=datetime.datetime.now()
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.warn_id
        except SQLAlchemyError as err:
            logging.error("Error adding member guild warning!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def revoke_warning(self, warn_id):
        """
        Docstring for revoke_warning
        
        :param warn_id: Which one to delete
        """
        warn_id = int(warn_id)

        session = get_session()
        try:
            record = (
                session.query(guild_member_warnings)
                .filter(
                    guild_member_warnings.warn_id == warn_id,
                    guild_member_warnings.guild_id == self.guild_id,
                )
                .one_or_none()
            )

            if not record:
                return False  # Nothing to delete

            session.delete(record)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def get_by_user(self, user_id):
        session = get_session()
        try:
            records = (
                session.query(guild_member_warnings)
                .filter(
                    guild_member_warnings.user_id == user_id,
                    guild_member_warnings.guild_id == self.guild_id
                )
                .all()
            )
        except SQLAlchemyError:
            return {}
        finally:
            session.close()

        parsed_data = {}
        for item in records:
            parsed_data[item.warn_id] = {
                "mod_id": item.moderator_id,
                "user_id": item.user_id,
                "reason": item.reason,
                "time": item.time,
                "guild_id": item.guild_id
            }
        return parsed_data
    
    def get_all(self):
        session = get_session()
        try:
            records = (
                session.query(guild_member_warnings)
                .filter(guild_member_warnings.guild_id == self.guild_id)
                .all()
            )
        except SQLAlchemyError:
            return {}
        finally:
            session.close()

        parsed_data = {}
        for item in records:
            parsed_data[item.warn_id] = {
                "mod_id": item.moderator_id,
                "user_id": item.user_id,
                "reason": item.reason,
                "time": item.time,
                "guild_id": item.guild_id
            }
        return parsed_data

class dbguild:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.set = automod_set(guild_id)
        self.get = automod_get(guild_id)
        self.wordlist = wordlist_modify(guild_id)
        self.muting = muting.guilds(guild_id)
        self.warnings = guild_warnings(guild_id)