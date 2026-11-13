from library.database.manage import (
    get_session,
    guild_leveling_exp,
    guild_leveling_role,
    observation_entry,
    guild_active_members,
    guild_activitiy_config,
    guild_leveling_config
)
from library.database.auditing import server_logs
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from library.botapp import botapp
from cachetools import TTLCache
from math import sqrt
import logging
import hikari

class guild_leveling:
    def __init__(self, guild_id:int):
        self.guild_id = guild_id
        self.msg_score_value = 5  # How many points 1 msg is worth

    def get_enabled(self):
        with get_session() as session:
            record = (
                session.query(guild_leveling_config)
                .filter(guild_leveling_config.guild_id == self.guild_id)
                .one_or_none()
            )
        return record.enabled if record else False

    def set_enabled(self, value:bool):
        with get_session() as session:
            record = (
                session.query(guild_leveling_config)
                .filter(guild_leveling_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_leveling_config(
                    guild_id=self.guild_id,
                    enabled=value
                )
                session.add(record)
                session.commit()
                return True
            record.enabled = value
            session.commit()
        return True

    def get_dedicated_channel(self):
        with get_session() as session:
            record = (
                session.query(guild_leveling_config)
                .filter(guild_leveling_config.guild_id == self.guild_id)
                .one_or_none()
            )
        return record.lvl_channel_id if record else None

    def set_dedicated_channel(self, channel_id):
        with get_session() as session:
            record = (
                session.query(guild_leveling_config)
                .filter(guild_leveling_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_leveling_config(
                    guild_id=self.guild_id
                )
                session.add(record)
                session.commit()
            else:
                record.lvl_channel_id = channel_id

        return True

    def estimate_user_level(self, user_id: int) -> int:
        user = self.get_user(user_id=user_id)

        if not user or not user.exp:
            return 0

        xp = user.exp

        # Solve: 10L^2 + 50L - XP = 0
        level = (-50 + sqrt(50**2 + 40 * xp)) / 20

        return max(0, int(level))

    def give_exp(self, user_id:int, exp:int=None, msgs:int=None, check_level:bool=False) -> True:
        if exp is None and msgs is None:
            raise ValueError("EXP or MSGS must be assigned and not be None.")
        elif exp and msgs:
            raise ValueError("EXP or MSGS cannot be both assigned.")

        with get_session() as session:
            record = (
                session.query(guild_leveling_exp)
                .filter(guild_leveling_exp.guild_id == self.guild_id)
                .filter(guild_leveling_exp.user_id == user_id)
                .one_or_none()
            )
            if not record:
                record = guild_leveling_exp(
                    guild_id=self.guild_id,
                    user_id=user_id,
                    exp=exp,
                    level=0
                )
                session.add(record)
                session.commit()
                session.refresh(record)
            old_lvl = record.level

            if exp:
                new_exp = int(record.exp + exp)
            elif msgs:
                new_exp = int(record.exp + (msgs * self.msg_score_value))
            else: 
                raise ValueError("Neither are truthy")

            user_lvl = self.estimate_user_level(user_id)

            record.level = user_lvl
            record.exp = new_exp
            session.commit()

        if check_level:
            return {
                "success": True,
                "lvl_is_diff": user_lvl != old_lvl,
                "old_lvl": old_lvl,
                "new_lvl": user_lvl
            }
        
        return True

    def remove_exp(self, user_id:int, exp:int=None, msgs:int=None, check_level:bool=False):
        if exp is None and msgs is None:
            raise ValueError("EXP or MSGS must be assigned and not be None.")
        elif exp and msgs:
            raise ValueError("EXP or MSGS cannot be both assigned.")

        with get_session() as session:
            record = (
                session.query(guild_leveling_exp)
                .filter(guild_leveling_exp.guild_id == self.guild_id)
                .filter(guild_leveling_exp.user_id == user_id)
                .one_or_none()
            )
            if not record:
                record = guild_leveling_exp(
                    guild_id=self.guild_id,
                    user_id=user_id,
                    exp=0,
                    level=0
                )
                session.add(record)
                session.commit()
                session.refresh(record)

            old_lvl = record.level
            
            # Don't let it fall below 0.
            if record.exp - exp <= 0:
                record.exp = 0
                record.level = 0
                session.commit()
                if check_level:
                    return {
                        "success": True,
                        "lvl_is_diff": 0 != old_lvl,
                        "old_lvl": old_lvl,
                        "new_lvl": 0
                    }
                else:
                    return True

            if exp:
                new_exp = int(record.exp - exp)
            elif msgs:
                new_exp = int(record.exp - (msgs * self.msg_score_value))
            else: 
                raise ValueError("Neither are truthy")
            
            user_lvl = self.estimate_user_level(user_id)

            record.level = user_lvl
            record.exp = new_exp
            session.commit()

        if check_level:
            return {
                "success": True,
                "lvl_is_diff": user_lvl != old_lvl,
                "old_lvl": old_lvl,
                "new_lvl": user_lvl
            }

        return True

    def get_leaderboard(self) -> list[guild_leveling_exp]:
        with get_session() as session:
            records = (
                session.query(guild_leveling_exp)
                .filter(guild_leveling_exp.guild_id == self.guild_id)
                .order_by(
                    guild_leveling_exp.exp.desc(),
                    guild_leveling_exp.user_id.asc()
                )  # Two order-by's. Just in case two people are tied for EXP.
                .all()
            )
            return records

    def get_leaderboard_position(self, user_id: int) -> int:
        with get_session() as session:
            user = (
                session.query(guild_leveling_exp)
                .filter(
                    guild_leveling_exp.guild_id == self.guild_id,
                    guild_leveling_exp.user_id == user_id
                )
                .first()
            )

            if user is None:
                return None

            position = (
                session.query(guild_leveling_exp)
                .filter(
                    guild_leveling_exp.guild_id == self.guild_id,
                    guild_leveling_exp.exp > user.exp
                )
                .count()
            )

            return position + 1

    def get_user(self, user_id:int) -> guild_leveling_exp:
        with get_session() as session:
            record = (
                session.query(guild_leveling_exp)
                .filter(guild_leveling_exp.guild_id == self.guild_id)
                .filter(guild_leveling_exp.user_id == user_id)
                .one_or_none()
            )
            return record
        return True

    def add_level_role(self, role_id:int, level_needed:int):
        """
        Let a role be given to a user when they reach a specific level
        """
        already_set = self.get_guild_level_perk(level_needed) is not None
        if already_set:
            return False

        with get_session() as session:
            try:
                record = guild_leveling_role(
                    guild_id=self.guild_id,
                    role_id=role_id,
                    level_needed=level_needed,
                )
                session.add(record)
                session.commit()
            except IntegrityError:
                return False
        return True

    def rm_level_role(self, role_id:int):
        """
        Let a role be given to a user when they reach a specific level
        """
        with get_session() as session:
            record = (
                session.query(guild_leveling_role)
                .filter(guild_leveling_role.role_id == role_id)
                .one_or_none()
            )
            session.delete(record)
            session.commit()
        return True

    def get_guild_perk_by_role(self, role_id:int) -> guild_leveling_role:
        with get_session() as session:
            record = (
                session.query(guild_leveling_role)
                .filter(guild_leveling_role.guild_id == self.guild_id)
                .filter(guild_leveling_role.role_id == role_id)
                .one_or_none()
            )
        return record

    def get_guild_level_perk(self, level:int) -> guild_leveling_role:
        with get_session() as session:
            record = (
                session.query(guild_leveling_role)
                .filter(guild_leveling_role.guild_id == self.guild_id)
                .filter(guild_leveling_role.level_needed == level)
                .one_or_none()
            )
        return record

class _ua_class:
    def __init__(self, is_active:bool, weekly_messages:list[observation_entry], level:int):
        self.is_active = is_active
        self.weekly_messages = weekly_messages
        self.level = level

guild_active_role_cache = TTLCache(maxsize=200, ttl=60)
guild_activity_enabled_cache = TTLCache(maxsize=200, ttl=60)

activity_threshold = 14  # Must have this many messages to be called active
activity_days_threshold = 7  # Must be the threshold of messages over this many days to be called active.

class user_activity:
    def __init__(self, guild_id:int):
        self.guild_id = guild_id

    @staticmethod
    async def scan_users_active():
        """
        Gets and applies the changes to each guild for each user. Can take a while to execute.
        """
        result = user_activity.determine_active()
        newly_active = result['newly_active']
        no_longer_active = result['no_longer_active']

        guilds_to_be_warned: list[list[int, str]] = []

        for guild_id, user_id in newly_active:
            ua = user_activity(guild_id)
            do_activity_monitoring = ua.get_guild_enabled()
            if do_activity_monitoring:
                role_id = ua.get_guild_active_role()
                try:
                    await botapp.rest.add_role_to_member(
                        guild=guild_id,
                        user=user_id,
                        role=role_id,
                        reason="User was flagged as being active in the community."
                    )
                except hikari.NotFoundError as err:
                    if guild_id not in guilds_to_be_warned:
                        errlower = err.message.lower()
                        if "role" in errlower:
                            guilds_to_be_warned.append([guild_id, "The active member role does not exist anymore, admins should assign a new role."])
                            ua.set_guild_active_role(None)
                            ua.set_guild_enabled(False)
                        elif "user" in errlower or "member" in errlower:
                            pass
                except hikari.ForbiddenError:
                    if guild_id not in guilds_to_be_warned:
                        guilds_to_be_warned.append([
                            guild_id,
                            f"We can't give or take the <@&{role_id}> role to users as we don't have sufficient permissions."
                        ])
                        ua.set_guild_enabled(False)

        for guild_id, user_id in no_longer_active:
            ua = user_activity(guild_id)
            do_activity_monitoring = ua.get_guild_enabled()
            if do_activity_monitoring:
                role_id = ua.get_guild_active_role()
                try:
                    await botapp.rest.remove_role_from_member(
                        guild=guild_id,
                        user=user_id,
                        role=role_id,
                        reason="User was flagged as no longer being active in the community."
                    )
                except hikari.NotFoundError as err:
                    if guild_id not in guilds_to_be_warned:
                        errlower = err.message.lower()
                        if "role" in errlower:
                            guilds_to_be_warned.append([guild_id, "The active member role does not exist anymore, admins should assign a new role."])
                            ua.set_guild_active_role(None)
                            ua.set_guild_enabled(False)
                        elif "user" in errlower or "member" in errlower:
                            pass
                except hikari.ForbiddenError:
                    if guild_id not in guilds_to_be_warned:
                        guilds_to_be_warned.append([
                            guild_id,
                            f"We can't give or take the <@&{role_id}> role to users as we don't have sufficient permissions."
                        ])
                        ua.set_guild_enabled(False)

        for item in guilds_to_be_warned:
            try:
                guild_id = item[0]
                problem = item[1]
            except IndexError as err:
                logging.error("Error attempting to unpack a list.", exc_info=err)
                continue
            await server_logs(guild_id).create_entry(
                hikari.Embed(
                    title="User Activity Error",
                    description=problem,
                    colour=0xff0000
                )
                .add_field(
                    name="Module Disabled",
                    value="User activity monitoring has been disabled until you fix the issue. To re-enable it, run `/activity toggle`."
                )
            )

        return True

    def get_guild_enabled(self):
        if guild_activity_enabled_cache.get(self.guild_id) is not None:
            return guild_activity_enabled_cache.get(self.guild_id)
        with get_session() as session:
            record = (
                session.query(guild_activitiy_config)
                .filter(guild_activitiy_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                return False
            guild_activity_enabled_cache[self.guild_id] = record.enabled
            return record.enabled

    def set_guild_enabled(self, enabled:bool):
        if guild_activity_enabled_cache.get(self.guild_id) is not None:
            del guild_activity_enabled_cache[self.guild_id]
        with get_session() as session:
            record = (
                session.query(guild_activitiy_config)
                .filter(guild_activitiy_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_activitiy_config(
                    guild_id=self.guild_id,
                    enabled=enabled
                )
                session.add(record)
            else:
                record.enabled = enabled
            session.commit()
        return True

    def get_guild_active_role(self):
        if guild_active_role_cache.get(self.guild_id) is not None:
            return guild_active_role_cache.get(self.guild_id)
        with get_session() as session:
            record = (
                session.query(guild_activitiy_config)
                .filter(guild_activitiy_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                return None
            guild_active_role_cache[self.guild_id] = record.active_role
            return record.active_role

    def set_guild_active_role(self, role_id:int) -> bool:
        if guild_active_role_cache.get(self.guild_id) is not None:
            del guild_active_role_cache[self.guild_id]
        with get_session() as session:
            record = (
                session.query(guild_activitiy_config)
                .filter(guild_activitiy_config.guild_id == self.guild_id)
                .one_or_none()
            )
            if not record:
                record = guild_activitiy_config(
                    guild_id=self.guild_id,
                    active_role=role_id
                )
                session.add(record)
            else:
                record.active_role = role_id
            session.commit()
        return True

    def get(self, user_id:int) -> _ua_class:
        with get_session() as session:
            records = (
                session.query(observation_entry)
                .filter(observation_entry.user_id == user_id)
                .filter(observation_entry.guild_id == self.guild_id)
                .filter(observation_entry.timestamp > (datetime.now() - timedelta(days=activity_days_threshold)))
                .all()
            )

            # If there's more than the threshold sent in the last 2 weeks, the user is active.
            is_active = len(records) >= activity_threshold

            constructed_class = _ua_class(
                is_active=is_active,
                weekly_messages=list(records),
                level=guild_leveling(self.guild_id).estimate_user_level(user_id)
            )

            self.set_active(user_id, is_active)

            return constructed_class

    def set_active(self, user_id:int, is_active:bool):
        with get_session() as session:
            activity_rec = (
                session.query(guild_active_members)
                .filter(guild_active_members.user_id == user_id)
                .filter(guild_active_members.guild_id == self.guild_id)
                .one_or_none()
            )
            if activity_rec is None:
                session.add(
                    guild_active_members(
                        guild_id=self.guild_id,
                        user_id=user_id,
                        is_active=is_active,
                        last_checked=datetime.now()
                    )
                )
                session.commit()
        return True

    def get_is_active(self, user_id:int):
        """
        Memory-based, may use old / outdated data.
        """
        with get_session() as session:
            activity_rec = (
                session.query(guild_active_members)
                .filter(guild_active_members.user_id == user_id)
                .filter(guild_active_members.guild_id == self.guild_id)
                .one_or_none()
            )

            if not activity_rec:
                is_active = self.is_user_active(user_id)
                return is_active
            
        return activity_rec.is_active

    def is_user_active(self, user_id: int) -> bool:
        """
        Checks whether a specific user is considered active in a specific guild.
        Returns True if their message count meets the activity threshold.
        """
        with get_session() as session:
            msg_count = (
                session.query(observation_entry)
                .filter(
                    observation_entry.guild_id == self.guild_id,
                    observation_entry.user_id == user_id,
                    observation_entry.timestamp > (
                        datetime.now() - timedelta(days=activity_days_threshold)
                    )
                )
                .count()
            )

        is_active = msg_count >= activity_threshold

        logging.info(
            f"User {user_id} is {'active' if is_active else 'not active'} "
            f"with {msg_count} messages in guild {self.guild_id}"
        )

        self.set_active(user_id, is_active)

        return is_active

    def get_msgs_count(self, user_id:int) -> int:
        with get_session() as session:
            count = (
                session.query(observation_entry)
                .filter(observation_entry.timestamp > (datetime.now() - timedelta(days=activity_days_threshold)))
                .filter(observation_entry.user_id == user_id)
                .count()
            )
        return count

    @staticmethod
    def get_all_users() -> list[guild_active_members]:
        with get_session() as session:
            activity_records = (
                session.query(guild_active_members)
                .all()
            )
            return activity_records

    @staticmethod
    def determine_active() -> dict[str, list[tuple[int, int]]]:
        """
        Scans the logs and finds out who's been talking in each guild, and who's not been.
        Returns a dict of 2 lists, 2 keys, first is "newly_active", 2nd is "no_longer_active".
        Key one of each tuple in the lists is guild_id, second is user_id.
        """
        with get_session() as session:
            records = (
                session.query(observation_entry)
                .filter(observation_entry.timestamp > (datetime.now() - timedelta(days=activity_days_threshold)))
                .all()
            )

        user_msg_counts: dict[int, dict[int, int]] = {}

        # Count messages per user in each guild.
        for record in records:
            guild_users = user_msg_counts.setdefault(record.guild_id, {})
            guild_users[record.user_id] = guild_users.get(record.user_id, 0) + 1

        # Build a set of users observed within the threshold for days.
        observed_users = {
            (record.guild_id, record.user_id)
            for record in records
        }

        # Include previously active users who haven't appeared in recent records.
        for user in user_activity.get_all_users():
            if user.is_active and (user.guild_id, user.user_id) not in observed_users:
                user_msg_counts.setdefault(user.guild_id, {})[user.user_id] = 0

        no_longer_active = []
        newly_active = []

        for guild_id, users in user_msg_counts.items():
            ua = user_activity(guild_id)

            for user_id, msg_count in users.items():
                active_prior = ua.get_is_active(user_id)
                is_active = msg_count >= activity_threshold
                
                log_msg = (
                    f"User {user_id} is {'active' if is_active else 'not active'} with {msg_count} messages "
                    f"in guild {guild_id}, Prior activity? {active_prior}"
                )
                logging.info(log_msg)

                ua.set_active(user_id, is_active=is_active)

                if active_prior and not is_active:
                    no_longer_active.append((guild_id, user_id))
                elif not active_prior and is_active:
                    newly_active.append((guild_id, user_id))

        return {
            "no_longer_active": no_longer_active,
            "newly_active": newly_active
        }
