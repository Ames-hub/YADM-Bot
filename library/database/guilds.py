from library.database.manage import (
    get_session,
    guild_text_automod_settings,
    guild_spam_automod_settings,
    guild_images_automod_settings,
    guild_automod_settings,
    member_violation,
    guild_custom_wordlist,
    mute_record,
    guild_member_warnings,
    guild_imagescan_threshold,
    guild_ban_record,
    guild_text_automod_text_checks,
    guild_text_automod_escalation_settings
)
from library.database.auditing import logs_config
from library.database.auditing import server_logs
from library.database.welcomer import welcomer
from sqlalchemy.exc import SQLAlchemyError
from library import datastore as ds 
from library.botapp import botapp
import datetime
import logging
import hikari
import io

class muting:
    class guilds:
        def __init__(self, guild_id:int):
            self.guild_id = int(guild_id)

        async def mute_member(self, user_id:int, reason:str, moderator_id:int, duration_s:int=600, hardmute:bool=False, is_cooldown:bool=False):
            """
            Mute a member in a guild for a specific amount of seconds.
            
            :param guild_id: Which guild it happens in
            :type guild_id: int
            :param user_id: The target to be muted
            :type user_id: int
            :param duration_s: How many seconds the mute should last.
            :type duration_s: int
            :param reason: Why they're being muted
            :type reason: str
            :param hardmute: Remove ALL other rolls from the individual except "muted". Vaguelly destructive.
            :type hardmute: bool
            :param is_cooldown: Whether this mute is just a cooldown (meaning a very short cooldown that happens shortly after a rule violation)
            """
            guild_id = self.guild_id
            user_id = int(user_id)

            muted_role = dbguild(guild_id).get.muted_role_id()
            if not muted_role:
                success = await self.create_muted_role()
                muted_role = dbguild(guild_id).get.muted_role_id()
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
                except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.NotFoundError):
                    return False

            # Checks if the user has an active mute (if so, there should only be one)
            existing_mutes = muting.list_all_mutes(active_only=True, user_id=user_id, guild_id=guild_id)
            if existing_mutes:
                # Check what roles the individual has, make sure they still have the muted role
                member = await botapp.rest.fetch_member(self.guild_id, user_id)
                member_roles = member.get_roles()
                if muted_role not in [role.id for role in member_roles]:
                    # If the user doesn't have the muted role, mark all mutes for this user as inactive
                    for mute in existing_mutes:
                        muting.set_mute_inactive(mute.case_id)
                else:
                    return existing_mutes[0].case_id  # Return the existing mute's case ID, we don't want to double-mute someone                    

            try:
                await botapp.rest.add_role_to_member(
                    guild=guild_id,
                    user=user_id,
                    role=muted_role,
                    reason="Member is being muted for: " + reason
                )
            except (hikari.ForbiddenError, hikari.NotFoundError):
                await server_logs(self.guild_id).create_entry(
                    hikari.Embed(
                        title="Cannot mute",
                        description=f"User <@{user_id}> cannot be muted as I cannot add the muted role to their account.",
                        colour=0x850101
                    )
                )
                return False

            if not is_cooldown:
                await server_logs(self.guild_id).create_entry(
                    hikari.Embed(
                        title="Member muted",
                        description=f"<@{user_id}> has been muted by <@{moderator_id}> until <t:{int(datetime.datetime.now().timestamp() + duration_s)}>",
                        colour=0x850101
                    )
                )

            # Make a record in the DB to say the person needs to be unmuted eventually
            session = get_session()
            try:
                record = mute_record(
                    user_id=user_id,
                    guild_id=guild_id,
                    scheduled_unmute=datetime.datetime.now().timestamp() + duration_s,
                    reason=reason,
                    moderator_id=moderator_id,
                    is_cooldown=is_cooldown
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record.case_id
            except SQLAlchemyError as err:
                logging.error("Error muting a member of a guild!", exc_info=err)
                session.rollback()
                return False
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
                    reason="Server did not have a pre-set muted role assigned for the bot.",
                    name="muted"
                )
            except hikari.ForbiddenError:
                return False
            
            # Get own top role and place muted role right below it,
            # so that the bot can still manage it but it will also over-ride as many other roles as possible
            try:
                me = await botapp.rest.fetch_member(self.guild_id, botapp.get_me().id)
                server_roles = await botapp.rest.fetch_roles(self.guild_id)
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.UnauthorizedError):
                return False

            my_top_role = me.get_top_role()
            muted_role_pos = my_top_role.position - 1

            roles_map = {}

            for role in server_roles:
                if role.id == new_role.id:
                    roles_map[muted_role_pos] = hikari.Snowflake(role.id)
                else:
                    roles_map[int(role.position)] = hikari.Snowflake(role.id)

            try:
                await botapp.rest.reposition_roles(
                    self.guild_id,
                    roles_map,
                    reason="Placing the muted role right below the bot's top role, so that it can manage it and over-ride as many roles as possible."
                )
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.UnauthorizedError):
                return False

            guild = dbguild(self.guild_id)
            success = guild.set.muted_role_id(new_role.id)
            return success

    def list_all_mutes(active_only=True, user_id:int=None, guild_id:int=None) -> list[mute_record]:
        session = get_session()
        try:
            if active_only:
                records = (
                    session.query(mute_record)
                    .filter(mute_record.active == True)
                )
            else:
                records = (
                    session.query(mute_record)
                )

            if user_id is not None:
                records = records.filter(mute_record.user_id == user_id)
            if guild_id is not None:
                records = records.filter(mute_record.guild_id == guild_id)

            return records.all()
        finally:
            session.close()

    def set_mute_inactive(mute_id):
        session = get_session()
        try:
            record = (
                session.query(mute_record)
                .filter(mute_record.case_id == mute_id)
                .one_or_none()
            )

            if not record:
                raise muting.errors.mute_not_found
            else:
                record.active = False

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
        guild_id:int,
        reporter_id: int,
        offender_id: int,
        time: datetime,
        violation: str,
        automated: bool,
        whistleblower: str,
        extra_info: str,
        relevant_img: io.BytesIO = None
    ) -> int:

        reporter_id = int(reporter_id)
        offender_id = int(offender_id)
        if not isinstance(time, datetime.datetime): raise TypeError(f"The time is not a datetime! Got \"{time}\" ({type(time)})")
        violation = str(violation)
        automated = bool(automated)

        session = get_session()
        try:
            record = member_violation(
                guild_id=guild_id,
                reporter_id=reporter_id,
                offender_id=offender_id,
                time=time,
                violation=violation,
                automated=automated,
                whistleblower=whistleblower,
                extra_info=extra_info,
                relevant_img=relevant_img
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

    def get_violation_record(entry_id: int) -> member_violation:
        session = get_session()
        try:
            record: member_violation = (
                session.query(member_violation)
                .filter(member_violation.entry_id == entry_id)
                .one_or_none()
            )
            return record
        finally:
            session.close()

    def get_violations_by_offender(offender_id: int) -> list[member_violation]:
        session = get_session()
        try:
            return (
                session.query(member_violation)
                .filter(member_violation.offender_id == offender_id)
                .order_by(member_violation.time.desc())
                .all()
            )
        finally:
            session.close()

class _image_filter_penalty_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id  

    def _get_record(self):
        session = get_session()
        try:
            return (
                session.query(guild_images_automod_settings)
                .filter(guild_images_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
        finally:
            session.close()

    def do_delete_msg(self):
        record = self._get_record()
        return record.penalty_delete_message if record else False

    def do_warn_member(self):
        record = self._get_record()
        return record.penalty_warn_member if record else False

    def do_mute_member(self):
        record = self._get_record()
        return record.penalty_mute_member if record else False

    def do_kick_member(self):
        record = self._get_record()
        return record.penalty_kick_member if record else False

    def do_ban_member(self):
        record = self._get_record()
        return record.penalty_ban_member if record else False

    def ban_duration(self):
        record = self._get_record()
        return record.ban_duration if record else False

    def get_mute_duration(self):
        record = self._get_record()
        return record.penalty_mute_duration if record else 60

    def get_ban_msg_purgetime(self):
        record = self._get_record()
        return record.ban_msg_purgetime if record else 600  # 10 minutes

    def do_cooldown(self):
        record = self._get_record()
        return record.do_cooldown if record else True

    def do_announce_infraction(self):
        record = self._get_record()
        return record.announce_infraction if record else False

    def do_announce_kick(self):
        record = self._get_record()
        return record.announce_kick if record else False

    def do_announce_ban(self):
        record = self._get_record()
        return record.announce_ban if record else False

class _spam_filter_penalty_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id    

    def _get_record(self):
        session = get_session()
        try:
            return (
                session.query(guild_spam_automod_settings)
                .filter(guild_spam_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
        finally:
            session.close()

    def mps_time_limit(self):
        record = self._get_record()
        return record.mps_time_limit if record else False

    def mps_limit(self):
        record = self._get_record()
        return record.mps_limit if record else False

    def do_delete_msg(self):
        record = self._get_record()
        return record.penalty_delete_message if record else False

    def do_warn_member(self):
        record = self._get_record()
        return record.penalty_warn_member if record else False

    def do_mute_member(self):
        record = self._get_record()
        return record.penalty_mute_member if record else False

    def do_kick_member(self):
        record = self._get_record()
        return record.penalty_kick_member if record else False

    def do_ban_member(self):
        record = self._get_record()
        return record.penalty_ban_member if record else False

    def ban_duration(self):
        record = self._get_record()
        return record.ban_duration if record else False

    def get_mute_duration(self):
        record = self._get_record()
        return record.penalty_mute_duration if record else 60

    def get_ban_msg_purgetime(self):
        record = self._get_record()
        return record.ban_msg_purgetime if record else 600  # 10 minutes

    def do_cooldown(self):
        record = self._get_record()
        return record.do_cooldown if record else True

    def do_announce_infraction(self):
        record = self._get_record()
        return record.announce_infraction if record else False

    def do_announce_kick(self):
        record = self._get_record()
        return record.announce_kick if record else False

    def do_announce_ban(self):
        record = self._get_record()
        return record.announce_ban if record else False

class _text_filter_checks_enabled_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _get_record(self) -> guild_text_automod_text_checks:
        session = get_session()
        try:
            return (
                session.query(guild_text_automod_text_checks)
                .filter(guild_text_automod_text_checks.guild_id == self.guild_id)
                .one_or_none()
            )
        finally:
            session.close()

    def equality_check(self):
        record = self._get_record()
        return record.equality_check if record else False

    def symbol_check(self):
        record = self._get_record()
        return record.symbol_check if record else False

    def collapsed_check(self):
        record = self._get_record()
        return record.collapsed_check if record else False

    def spacehack_check(self):
        record = self._get_record()
        return record.spacehack_check if record else False

    def letter_stitch_check(self):
        record = self._get_record()
        return record.letter_stitch_check if record else False

    def reverse_check(self):
        record = self._get_record()
        return record.reverse_check if record else False
    
    def similarity_check(self):
        record = self._get_record()
        return record.similarity_check if record else False

    def syntactic_analysis(self):
        record = self._get_record()
        return record.syntactic_analysis if record else False

class text_filter_penalties_escalation_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _get_record(self) -> guild_text_automod_escalation_settings:
        with get_session() as session:
            record = (
                session.query(guild_text_automod_escalation_settings)
                .filter(guild_text_automod_escalation_settings.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_text_automod_escalation_settings(
                    guild_id=self.guild_id
                )
                session.add(record)
                session.commit()
                record = (
                    session.query(guild_text_automod_escalation_settings)
                    .filter(guild_text_automod_escalation_settings.guild_id == self.guild_id)
                    .one_or_none()
                )
            return record

    def msg_deletion(self):
        record = self._get_record()
        return record.del_msg_threshold

    def cooldown_threshold(self):
        record = self._get_record()
        return record.cooldown_threshold

    def mute_threshold(self):
        record = self._get_record()
        return record.mute_threshold

    def kick_member(self):
        record = self._get_record()
        return record.kick_member_threshold

    def ban_member(self):
        record = self._get_record()
        return record.ban_member_threshold

class _text_filter_penalty_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.checks = _text_filter_checks_enabled_get(guild_id)
        self.escalation = text_filter_penalties_escalation_get(guild_id)

    def _get_record(self):
        with get_session() as session:
            record = (
                session.query(guild_text_automod_settings)
                .filter(guild_text_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_text_automod_settings(
                    guild_id=self.guild_id
                )
                session.add(record)
                session.commit()
                record = (
                    session.query(guild_text_automod_settings)
                    .filter(guild_text_automod_settings.guild_id == self.guild_id)
                    .one_or_none()
                )
            return record

    def do_delete_msg(self):
        record = self._get_record()
        return record.penalty_delete_message if record else False

    def do_warn_member(self):
        record = self._get_record()
        return record.penalty_warn_member if record else False

    def do_mute_member(self):
        record = self._get_record()
        return record.penalty_mute_member if record else False

    def do_kick_member(self):
        record = self._get_record()
        return record.penalty_kick_member if record else False

    def do_ban_member(self):
        record = self._get_record()
        return record.penalty_ban_member if record else False
    
    def ban_duration(self):
        record = self._get_record()
        return record.ban_duration if record else False

    def get_mute_duration(self):
        record = self._get_record()
        return record.penalty_mute_duration if record else 60

    def get_ban_msg_purgetime(self):
        record = self._get_record()
        return record.ban_msg_purgetime if record else 600  # 10 minutes

    def similarity_threshold(self):
        record = self._get_record()
        return record.sim_check_threshold if record else 0.85

    def do_cooldown(self):
        record = self._get_record()
        return record.do_cooldown if record else True

    def do_announce_infraction(self):
        record = self._get_record()
        return record.announce_infraction if record else False

    def do_announce_kick(self):
        record = self._get_record()
        return record.announce_kick if record else False

    def do_announce_ban(self):
        record = self._get_record()
        return record.announce_ban if record else False

    def use_preset_swears_list(self):
        record = self._get_record()
        return record.use_preset_swears_list if record else False  # most people are fine with swearing.
    
    def use_preset_slurs_list(self):
        record = self._get_record()
        return record.use_preset_slurs_list if record else True
    
    def use_preset_lessnsfw_list(self):
        record = self._get_record()
        return record.use_preset_lessnsfw_list if record else False

    def use_preset_hardnsfw_list(self):
        record = self._get_record()
        return record.use_preset_hardnsfw_list if record else True

class automod_get:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.text = _text_filter_penalty_get(guild_id)
        self.spam = _spam_filter_penalty_get(guild_id)
        self.images = _image_filter_penalty_get(guild_id)

    def _get_record(self):
        session = get_session()
        try:
            record = (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_automod_settings(
                    guild_id=self.guild_id
                )
                session.add(record)
                session.commit()
                # Re-fetch item
                record = (
                    session.query(guild_automod_settings)
                    .filter(guild_automod_settings.guild_id == self.guild_id)
                    .one_or_none()
                )
        finally:
            session.close()

    def do_escalate(self):
        record = self._get_record()
        return record.do_escalate

    def escalation_window(self):
        record = self._get_record()
        return record.escalation_window

    def muted_role_id(self):
        record = self._get_record()
        return record.muted_role_id if record else None

    def do_image_filtering(self):
        record = self._get_record()
        return record.do_image_filtering if record else None

    def do_filter_spam(self):
        record = self._get_record()
        return record.do_filter_spam if record else None
    
    def do_text_scan(self):
        record = self._get_record()
        return record.do_text_scan if record else None

    def nsfw_scan_threshold(self):
        session = get_session()
        try:
            return (
                session.query(guild_imagescan_threshold.threshold)
                .filter(guild_imagescan_threshold.guild_id == self.guild_id)
                .one_or_none()
            )
        finally:
            session.close()

class _text_filter_checks_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_text_automod_text_checks)
                .filter(guild_text_automod_text_checks.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_text_automod_text_checks(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating text automod settings for which checks are enabled!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def equality_check(self, value:bool):
        return self._update(equality_check=value)

    def symbol_check(self, value: bool):
        return self._update(symbol_check=value)

    def collapsed_check(self, value: bool):
        return self._update(collapsed_check=value)

    def spacehack_check(self, value: bool):
        return self._update(spacehack_check=value)

    def letter_stitch_check(self, value: bool):
        return self._update(letter_stitch_check=value)

    def reverse_check(self, value: bool):
        return self._update(reverse_check=value)

    def similarity_check(self, value: bool):
        return self._update(similarity_check=value)
    
    def syntactic_analysis(self, value: bool):
        return self._update(syntactic_analysis=value)

class text_filter_penalties_escalation_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_text_automod_escalation_settings)
                .filter(guild_text_automod_escalation_settings.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_text_automod_escalation_settings(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating text automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def msg_deletion(self, value:int):
        return self._update(del_msg_threshold=value)

    def cooldown_threshold(self, value:int):
        return self._update(cooldown_threshold=value)

    def mute_threshold(self, value:int):
        return self._update(mute_threshold=value)

    def kick_member(self, value:int):
        return self._update(kick_member_threshold=value)

    def ban_member(self, value:int):
        return self._update(ban_member_threshold=value)

class _text_filter_penalties_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.checks = _text_filter_checks_set(guild_id)
        self.escalation = text_filter_penalties_escalation_set(guild_id)

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_text_automod_settings)
                .filter(guild_text_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_text_automod_settings(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating text automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

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
    
    def ban_duration(self, seconds: int):
        return self._update(ban_duration=seconds)

    def set_ban_msg_purgetime(self, seconds: int):
        return self._update(ban_msg_purgetime=seconds)

    def similarity_threshold(self, value: float):
        return self._update(sim_check_threshold=value)

    def do_cooldown(self, value: bool):
        return self._update(do_cooldown=value)

    def do_announce_infraction(self, value: bool):
        return self._update(announce_infraction=value)

    def do_announce_kick(self, value: bool):
        return self._update(announce_kick=value)
    
    def do_announce_ban(self, value: bool):
        return self._update(announce_ban=value)

    def use_preset_swears_list(self, value: bool):
        result = self._update(use_preset_swears_list=value)
        # Make sure this is consistent everywhere to avoid stale data, the moment it changes, its got to be deleted.
        if result and ds.d["bad_word_list_cache"].get(self.guild_id, None):
            del ds.d["bad_word_list_cache"][self.guild_id]
        return result

    def use_preset_slurs_list(self, value: bool):
        result = self._update(use_preset_slurs_list=value)
        if result and ds.d["bad_word_list_cache"].get(self.guild_id, None):
            del ds.d["bad_word_list_cache"][self.guild_id]
        return result

    def use_preset_lessnsfw_list(self, value: bool):
        result = self._update(use_preset_lessnsfw_list=value)
        if result and ds.d["bad_word_list_cache"].get(self.guild_id, None):
            del ds.d["bad_word_list_cache"][self.guild_id]
        return result

    def use_preset_hardnsfw_list(self, value: bool):
        result = self._update(use_preset_hardnsfw_list=value)
        if result and ds.d["bad_word_list_cache"].get(self.guild_id, None):
            del ds.d["bad_word_list_cache"][self.guild_id]
        return result

class _spam_filter_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_spam_automod_settings)
                .filter(guild_spam_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_spam_automod_settings(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating spam automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def mps_time_limit(self, value:int):
        return self._update(mps_time_limit=value)

    def mps_limit(self, value:int):
        return self._update(mps_limit=value)

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

    def ban_duration(self, seconds: int):
        return self._update(ban_duration=seconds)

    def set_ban_msg_purgetime(self, seconds: int):
        return self._update(ban_msg_purgetime=seconds)

    def do_cooldown(self, value: bool):
        return self._update(do_cooldown=value)

    def do_announce_infraction(self, value: bool):
        return self._update(announce_infraction=value)

    def do_announce_kick(self, value: bool):
        return self._update(announce_kick=value)
    
    def do_announce_ban(self, value: bool):
        return self._update(announce_ban=value)

class _image_filter_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    def _update(self, **fields):
        session = get_session()
        try:
            record = (
                session.query(guild_images_automod_settings)
                .filter(guild_images_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_images_automod_settings(
                    guild_id=self.guild_id,
                    **fields
                )
                session.add(record)
            else:
                for key, value in fields.items():
                    setattr(record, key, value)

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating image automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

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

    def ban_duration(self, seconds: int):
        return self._update(ban_duration=seconds)

    def set_ban_msg_purgetime(self, seconds: int):
        return self._update(ban_msg_purgetime=seconds)

    def do_cooldown(self, value: bool):
        return self._update(do_cooldown=value)

    def do_announce_infraction(self, value: bool):
        return self._update(announce_infraction=value)

    def do_announce_kick(self, value: bool):
        return self._update(announce_kick=value)
    
    def do_announce_ban(self, value: bool):
        return self._update(announce_ban=value)

class automod_set:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.text = _text_filter_penalties_set(guild_id)
        self.spam = _spam_filter_set(guild_id)
        self.images = _image_filter_set(guild_id)

    def do_escalate(self, value:bool):
        value = bool(value)
        with get_session() as session:
            record = (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_automod_settings(
                    guild_id=self.guild_id,
                    do_escalate=value
                )
                session.add(record)
            else:
                record.do_escalate = value
            session.commit()
        return True

    def escalation_window(self, value:int):
        value = int(value)
        with get_session() as session:
            record = (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_automod_settings(
                    guild_id=self.guild_id,
                    escalation_window=value
                )
                session.add(record)
            else:
                record.escalation_window = value
            session.commit()
        return True

    def nsfw_scan_threshold(self, threshold:float):
        session = get_session()
        try:
            record = (
                session.query(guild_imagescan_threshold)
                .filter(guild_imagescan_threshold.guild_id == self.guild_id)
                .one_or_none()
            )

            if not record:
                record = guild_imagescan_threshold(
                    guild_id=self.guild_id,
                    threshold=threshold
                )
                session.add(record)
            else:
                record.threshold = threshold

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating image automod threshold settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def muted_role_id(self, value: int):
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
                    muted_role_id=value
                )
                session.add(record)
            else:
                record.muted_role_id = value

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error updating mute role ID automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def do_image_filtering(self, value: bool):
        return self._update_main(do_image_filtering=value)

    def do_filter_spam(self, value: bool):
        return self._update_main(do_filter_spam=value)

    def do_text_scan(self, value: bool):
        return self._update_main(do_text_scan=value)

    def use_wordlist_swears(self, value: bool):
        return self._update_main()

    def _update_main(self, **fields):
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
        except SQLAlchemyError as err:
            logging.error("Error updating automod settings!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

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
            if ds.d["bad_word_list_cache"].get(self.guild_id, None):
                del ds.d["bad_word_list_cache"][self.guild_id]
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
            if ds.d["bad_word_list_cache"].get(self.guild_id, None):
                del ds.d["bad_word_list_cache"][self.guild_id]
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
        except SQLAlchemyError as err:
            logging.error("Error getting the word list", exc_info=err)
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

    def get_by_user(self, user_id, escalation_window:int=None):
        session = get_session()
        try:
            records = (
                session.query(guild_member_warnings)
                .filter(
                    guild_member_warnings.user_id == user_id,
                    guild_member_warnings.guild_id == self.guild_id
                )
            )
            if escalation_window:
                escalation_window_start = datetime.datetime.fromtimestamp(
                    (datetime.datetime.now().timestamp() - escalation_window)
                )
                records = records.filter(guild_member_warnings.time >= escalation_window_start)
            records = records.all()
            return records
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

# A duplicate of guild_bans.list_bans that doesn't filter by guild
def list_all_bans() -> list[guild_ban_record]:
    session = get_session()
    try:
        records = (session.query(guild_ban_record)).all()
        return records
    except SQLAlchemyError as err:
        logging.error("Failed listing all bans!", exc_info=err)
        return []  # Return an empty list if something goes wrong
    finally:
        session.close()

class guild_bans:
    def __init__(self, guild_id:int):
        self.guild_id = int(guild_id)

    async def unban_user(self, user_id:int, reason:str):
        ban = self.fetch_ban(user_id)

        try:
            await botapp.rest.unban_member(
                ban.guild_id,
                ban.banned_id,
                reason=reason
            )
        except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
            return False
        
        logs = server_logs(self.guild_id)
        await logs.create_entry(
            hikari.Embed(
                title="User unbanned",
                description=f"<@{ban.banned_id}> was unbanned from the server.",
                color=0x0000ff
            )
            .add_field(
                name="Original Reason for ban",
                value=ban.reason
            )
        )

    async def ban_user(
            self, banned_id:int,
            moderator_id:int,
            msg_del_duration:int,
            ban_seconds:int,
            reason:str,
            announce_ban:bool,
            infraction_id:int=None
        ) -> bool:
        if ban_seconds <= 0:
            return -1

        # Check our cache
        cache_expire_time = 86400  # 1 day in seconds
        timestamp_now = datetime.datetime.now().timestamp()
        cache_obj = ds.d["guild_name_cache"].get(self.guild_id, None)
        guild_name = None
        if cache_obj:
            if not timestamp_now - cache_obj['time'] >= cache_expire_time:
                guild_name = cache_obj['name']
            if not guild_name:
                # Get from discord, add to cache.
                discord_guild = await botapp.rest.fetch_guild(self.guild_id)
                ds.d["guild_name_cache"][self.guild_id] = {"name": discord_guild.name, "time": timestamp_now}
                guild_name = discord_guild.name

        if not infraction_id:
            automated = moderator_id == ds.d['myid']
            case_id = violations.create_member_violation(
                guild_id=self.guild_id,
                reporter_id=moderator_id,
                offender_id=banned_id,
                time=datetime.datetime.now(),
                violation=reason,
                automated=automated,
                whistleblower="Unknown" if automated else "User-triggered",
                extra_info=None
            )

        if announce_ban:
            msg_send_success = True
            try:
                banned_user = await botapp.rest.fetch_member(self.guild_id, banned_id)

                msg = await banned_user.send(
                    embed=hikari.Embed(
                        title="Banished",
                        description=f"You've been detected as breaking the rules of {guild_name} and have been banned.\nReason: {reason}",
                        colour=0xff0000
                    )
                )
            except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
                msg_send_success = False

        try:
            await botapp.rest.ban_user(
                self.guild_id,
                banned_id,
                delete_message_seconds=msg_del_duration,
                reason=reason
            )
        except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
            if announce_ban:
                if msg_send_success:
                    await msg.delete()
                    del msg
            return False

        time_to_unban = datetime.datetime.now().timestamp() + ban_seconds

        # Add an entry to the database to track their unban timer
        case_id = self.track_ban(
            infraction_id=infraction_id,
            banned_id=banned_id,
            moderator_id=moderator_id,
            time_to_unban=time_to_unban,
            reason=reason,
            return_case_id=True
        )

        await server_logs(self.guild_id).create_entry(
            hikari.Embed(
                title=f"User Banned (Case {case_id})",
                description=f"<@{banned_id}> Has been banned until <t:{time_to_unban}> for:\n{reason}",
                colour=0xff0000
            )
        )
        return True

    def track_ban(self, infraction_id:int, banned_id:int, moderator_id, time_to_unban:int, reason:str, return_case_id:bool=False):
        session = get_session()
        try:
            record = guild_ban_record(
                case_id=infraction_id,
                guild_id=self.guild_id,
                banned_id=banned_id,
                moderator_id=moderator_id,
                time_to_unban=datetime.datetime.fromtimestamp(time_to_unban),
                reason=reason
            )
            session.add(record)
            session.commit()
            session.refresh()
            if return_case_id:
                return record.case_id
            else:
                return True
        except SQLAlchemyError as err:
            logging.error("Error adding member ban record!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def list_bans(self) -> list[guild_ban_record]:
        session = get_session()
        try:
            records = (
                session.query(guild_ban_record)
                .filter(guild_ban_record.guild_id == self.guild_id)
                .all()
            )
            return records
        except SQLAlchemyError as err:
            logging.error("Failed listing all bans!", exc_info=err)
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

    def fetch_ban(self, user_id) -> guild_ban_record:
        session = get_session()
        try:
            records = (
                session.query(guild_ban_record)
                .filter(guild_ban_record.guild_id == self.guild_id)
                .filter(guild_ban_record.banned_id == user_id)
                .one_or_none()
            )
            return records
        except SQLAlchemyError as err:
            logging.error("Failed listing all bans!", exc_info=err)
            return None
        finally:
            session.close()

class dbguild:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.set = automod_set(guild_id)
        self.get = automod_get(guild_id)
        self.wordlist = wordlist_modify(guild_id)
        self.muting = muting.guilds(guild_id)
        self.warnings = guild_warnings(guild_id)
        self.bans = guild_bans(guild_id)
        self.logs_config = logs_config(guild_id)
        self.welcomer = welcomer(guild_id)

    def set_automod_defaults(self):
        # Enters the guild ID into a line in the table, which auto-gens defaults.
        if self.exists_in_db():
            return False  # Can't do it if we already exist here though.
        with get_session() as session:
            record = guild_text_automod_text_checks(
                guild_id=self.guild_id
            )
            session.add(record)
            session.commit()
        return True

    async def find_name(self):
        # TODO: Make this cache the name for max 7 days.
        guild = await botapp.rest.fetch_guild(self.guild_id)
        return guild.name

    async def handle_like_guilty(self, user_id:int, reason=None, mod_id:int=None, relevant_msg: tuple[int, int]=None, whistleblower:str=None):
        """
        A function that handles a user as if they are guilty and had tripped the automod.
        It handles it like this even if they are not guilty of any misconduct. This bypasses observe-only.

        relevant_msg must be provided as a tuple (if provided at all.) The tuple must be (channel_id, message_id)
        """
        # Check lightbulb cache (note: its practically useless since lightbulb's cache never seems to cache anything. Or I'm doing it wrong.)
        guild = dbguild(self.guild_id)
        guild_name = self.find_name()
        logs = server_logs(self.guild_id)
        guild_name = await self.find_name()
        if not reason:
            reason = "No reason provided for moderation actions."
        violation = (
            f"User <@{user_id}> (ID {user_id}) was prosecuted by <@{mod_id}> with reason: {reason}"
        )

        cat_check = guild.get.text
        # Always add the violation for the record.
        case_id = violations.create_member_violation(
            guild_id=self.guild_id,
            reporter_id=mod_id,
            offender_id=user_id,
            time=datetime.datetime.now(),
            violation=violation,
            automated=True,
            whistleblower="None" if not whistleblower else whistleblower
        )

        # IF it so happens that the violation has a problem and doesn't get created, we should just return and not attempt any punishment actions.
        if not case_id:
            return False

        do_mute_member = cat_check.do_mute_member()

        # if we're not to mute, put them on cooldown if told to do so. (Cooldown is a short, short mute)
        if cat_check.do_cooldown() and not do_mute_member:
            await guild.muting.mute_member(
                user_id=user_id,
                reason="VIOLATION AUTO COOLDOWN: " + violation,
                moderator_id=mod_id,
                duration_s=30,  # 30 sec mute for spam. TODO: Make this configurable.
                is_cooldown=True
            )

        if relevant_msg:
            do_del_msg = cat_check.do_delete_msg()
            if do_del_msg:
                if type(relevant_msg) is int:
                    message = await botapp.rest.fetch_message(relevant_msg[0], relevant_msg[1])
                    await message.delete()
                else:  # Assume its the message object
                    await relevant_msg.delete()

        if cat_check.do_warn_member():
            guild.warnings.add_warning(
                reason=violation,
                mod_id=mod_id,
                user_id=user_id,
            )
        if do_mute_member:
            mute_duration = cat_check.get_mute_duration()
            await guild.muting.mute_member(
                user_id=user_id,
                moderator_id=mod_id,
                reason=violation,
                duration_s=mute_duration,
            )

        try:
            member = await botapp.rest.fetch_member(self.guild_id, user_id)
        except hikari.ForbiddenError:
            await logs.create_entry(
                hikari.Embed(
                    title="Error muting User!",
                    description=f"I couldn't fetch {member.mention} to handle the following violation!\nViolation: {violation}",
                    colour=0xff0000
                )
            )
            return False

        if cat_check.do_kick_member():
            msg_sent = True
            if cat_check.do_announce_kick():
                try:
                    msg = await member.send(
                        embed=hikari.Embed(
                            title="Kicked",
                            description=f"You've been detected as breaking the rules of {guild_name} and have been kicked.\nReason: {violation}"
                        )
                    )
                except (hikari.ForbiddenError, hikari.BadRequestError, hikari.UnauthorizedError):
                    msg_sent = False

            try:
                await member.kick(reason=violation)
            except (hikari.ForbiddenError, hikari.UnauthorizedError):
                await logs.create_entry(
                    hikari.Embed(
                        title="Error Kicking User!",
                        description=f"I couldn't kick {member.mention} even though they broke rules!\nViolation: {violation}",
                        colour=0xff0000
                    )
                )
                if msg_sent:
                    await msg.delete()
                    del msg
        if cat_check.do_ban_member():
            delete_msg_seconds = cat_check.get_ban_msg_purgetime()

            announce_ban = cat_check.do_announce_ban()
            if announce_ban:
                try:
                    await guild.bans.ban_user(
                        case_id=case_id,
                        banned_id=user_id,
                        moderator_id=botapp.get_me().id,
                        msg_del_duration=delete_msg_seconds,
                        ban_seconds=cat_check.ban_duration(),
                        reason=violation,
                        announce_ban=announce_ban
                    )
                except hikari.ForbiddenError:
                    await logs.create_entry(
                        hikari.Embed(
                            title="Error Banning User!",
                            description=f"I couldn't ban <@{user_id}> even though they broke rules!\nViolation: {violation}",
                            colour=0xff0000
                        )
                    )

        logs_embed = (
            hikari.Embed(
                title="Rule Violation Detected",
                description=violation,
                colour=0xff0000
            )
            .set_author(name=member.display_name, icon=member.display_avatar_url)
        )

        await logs.create_entry(logs_embed)

        return case_id

    async def set_recommended_settings(self):
        await self.logs_config.mk_logs_channel()

        self.set.do_image_filtering(True)
        self.set.do_text_scan(True)
        self.set.do_filter_spam(True)

        # Configure word lists
        self.set.text.use_preset_swears_list(True)
        self.set.text.use_preset_slurs_list(True)
        self.set.text.use_preset_lessnsfw_list(False)
        self.set.text.use_preset_hardnsfw_list(True)

        # Configure text punishments
        self.set.text.do_announce_infraction(True)
        self.set.text.do_delete_msg(True)
        self.set.text.do_warn_member(True)
        self.set.text.do_cooldown(True)
        self.set.text.do_kick_member(False)
        self.set.text.do_ban_member(False)
        self.set.text.do_mute_member(True)
        self.set.text.set_mute_duration(604800)
        self.set.text.checks.equality_check(True)
        self.set.text.checks.symbol_check(True)
        self.set.text.checks.collapsed_check(True)
        self.set.text.checks.spacehack_check(True)
        self.set.text.checks.letter_stitch_check(True)
        self.set.text.checks.reverse_check(True)
        self.set.text.checks.similarity_check(True)
        self.set.text.checks.syntactic_analysis(True)

        # Configure text punishment escalation
        self.set.text.escalation.msg_deletion(1)
        self.set.text.escalation.cooldown_threshold(2)
        self.set.text.escalation.mute_threshold(3)

        # Set spam rule  settings
        self.set.spam.do_announce_infraction(True)
        self.set.spam.do_cooldown(True)
        self.set.spam.do_kick_member(False)
        self.set.spam.do_ban_member(False)
        self.set.spam.do_delete_msg(True)
        self.set.spam.do_warn_member(True)

        # Set image rule settings
        self.set.images.do_announce_infraction(True)
        self.set.images.do_cooldown(True)
        self.set.images.do_kick_member(False)
        self.set.images.do_ban_member(False)
        self.set.images.do_delete_msg(True)
        self.set.images.do_warn_member(True)
        self.set.nsfw_scan_threshold(0.95)

        return True

    async def purge_messages(self, moderator_id:int, channel_id:int, after:datetime.datetime=None, messages_list:list=None, reason: str="No reason provided"):
        if not after and not messages_list:
            raise ValueError("Must provide at least 'after', or 'messages to purge' list")
        elif messages_list and after:
            raise ValueError("Cannot provide both 'after' and 'messages to purge' list")

        if after:
            two_weeks = 1209600  # 14 days in seconds
            if (datetime.datetime.now() - after).total_seconds() > two_weeks:
                raise ValueError("Cannot bulk delete messages older than 14 days due to Discord limitations.")

        messages_list = []
        if messages_list:
            messages_list = messages_list
        else:
            try:
                fetched_messages = botapp.rest.fetch_messages(channel_id, after=after)
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
                return False
            async for message in fetched_messages:
                messages_list.append(message.id)

        log_msg = f"{len(messages_list)} messages were purged from <#{channel_id}> by <@{moderator_id}>.\nReason: {reason}"
        await server_logs(self.guild_id).create_entry(
            hikari.Embed(
                title="Messages Purged",
                description=log_msg,
                color=0xFFD580
            )
        )

        try:
            await botapp.rest.delete_messages(
                channel_id,
                messages_list,
                reason=f"Moderator: <@{moderator_id}> | Reason: {reason}"
            )
            return True
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.UnauthorizedError):
            return False
        except hikari.BulkDeleteError as err:
            logging.error("Bulk delete error during message purge!", exc_info=err)
            return False

    def exists_in_db(self):
        session = get_session()
        try:
            return (
                session.query(guild_automod_settings)
                .filter(guild_automod_settings.guild_id == self.guild_id)
                .one_or_none()
                is not None
            )
        finally:
            session.close()

    def create(self):
        """
        Inserts the default row for a guild into the database. This should only be used once per guild.
        """
        if not self.exists_in_db():
            session = get_session()
            try:
                record = guild_automod_settings(guild_id=self.guild_id)
                session.add(record)
                session.commit()
            except SQLAlchemyError as err:
                logging.error("Error creating guild automod settings!", exc_info=err)
                session.rollback()
                return False
            finally:
                session.close()