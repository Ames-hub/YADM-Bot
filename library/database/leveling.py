from library.database.manage import (
    get_session,
    guild_leveling_exp,
    guild_leveling_role,
    observation_entry,
    guild_active_members,
    guild_activitiy_config,
    guild_leveling_config,
    guild_activitiy_role_perk,
    guild_activitiy_perks_given
)
from datetime import datetime, timedelta, timezone
from library.database.auditing import server_logs
from sqlalchemy.exc import IntegrityError
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
                    guild_id=self.guild_id,
                    lvl_channel_id=channel_id,
                )
                session.add(record)
            else:
                record.lvl_channel_id = channel_id

            session.commit()

        return True

    def estimate_user_level(self, user_id: int) -> int:
        user = self.get_user(user_id=user_id)

        if not user or not user.exp:
            return 0

        xp = user.exp

        # Solve: 10L^2 + 50L - XP = 0
        level = (-50 + sqrt(50**2 + 40 * xp)) / 20

        return max(0, int(level))

    def _compute_user_level(self, exp: int) -> int:
        if not exp or exp <= 0:
            return 0
        return max(0, int((-50 + sqrt(50 ** 2 + 40 * exp)) / 20))

    def give_exp(
        self,
        user_id: int,
        exp: int = None,
        msgs: int = None,
        check_level: bool = False,
    ):
        if exp is None and msgs is None:
            raise ValueError("EXP or MSGS must be assigned and not be None.")
        if exp is not None and msgs is not None:
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
                    level=0,
                )
                session.add(record)
                session.flush()  # makes the row visible in-session without committing

            old_lvl = record.level or 0

            if exp is not None:
                delta = int(exp)
            elif msgs is not None:
                delta = int(msgs) * self.msg_score_value
            else:
                raise ValueError("Neither exp nor msgs was provided.")  # defensive

            # Clamp at 0 for symmetry with remove_exp; also guards against negative `exp`.
            new_exp = max(0, int(record.exp or 0) + delta)
            record.exp = new_exp

            user_lvl = self._compute_user_level(new_exp)
            record.level = user_lvl

            session.commit()

        if check_level:
            return {
                "success": True,
                "lvl_is_diff": user_lvl != old_lvl,
                "old_lvl": old_lvl,
                "new_lvl": user_lvl,
            }

        return True

    def remove_exp(
        self,
        user_id: int,
        exp: int = None,
        msgs: int = None,
        check_level: bool = False,
    ):
        if exp is None and msgs is None:
            raise ValueError("EXP or MSGS must be assigned and not be None.")
        if exp is not None and msgs is not None:
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
                    level=0,
                )
                session.add(record)
                session.flush()

            old_lvl = record.level or 0

            if exp is not None:
                delta = int(exp)
            elif msgs is not None:
                delta = int(msgs) * self.msg_score_value
            else:
                raise ValueError("Neither exp nor msgs was provided.")  # defensive

            new_exp = max(0, int(record.exp or 0) - delta)
            record.exp = new_exp

            user_lvl = self._compute_user_level(new_exp)
            record.level = user_lvl

            session.commit()

        if check_level:
            return {
                "success": True,
                "lvl_is_diff": user_lvl != old_lvl,
                "old_lvl": old_lvl,
                "new_lvl": user_lvl,
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

    def get_leaderboard_position(self, user_id: int) -> int | None:
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
                .filter(guild_leveling_role.guild_id == self.guild_id)
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

class UserActivitySnapshot:
    def __init__(self, is_active:bool, weekly_messages:list[observation_entry], level:int):
        self.is_active = is_active
        self.weekly_messages = weekly_messages
        self.level = level

def _perk_matches(perk: guild_activitiy_role_perk, count: int) -> bool:
    op = perk.operator
    if op == "GTE": return count >= perk.msgs_required
    if op == "GT":  return count >  perk.msgs_required
    if op == "LTE": return count <= perk.msgs_required
    if op == "LT":  return count <  perk.msgs_required
    raise ValueError(f"Unknown operator {op!r} on perk {perk.role_id}")

guild_active_role_cache = TTLCache(maxsize=200, ttl=60)
guild_activity_enabled_cache = TTLCache(maxsize=200, ttl=60)
guild_perks_roleid_cache = TTLCache(maxsize=500, ttl=60)  # Can be accessed as dict[role_id: guild_activitiy_role_perk]
guild_perks_by_guild_cache = TTLCache(maxsize=200, ttl=60)
activity_threshold = 7  # Must have this many messages to be called active
activity_days_threshold = 7  # Must be the threshold of messages over this many days to be called active.

class user_activity:
    def __init__(self, guild_id:int):
        self.guild_id = guild_id

    class errors:
        class perk_exists(Exception):
            def __init__(self, *args, record: guild_activitiy_role_perk):
                super().__init__(*args)
                self.record = record
        class perk_not_found(Exception):
            def __init__(self, *args):
                super().__init__(*args)

    @staticmethod
    async def scan_perk_eligable() -> bool:
        """
        Scans for users who are eligable to get activity perks and gives them the perks.
        """
        eligable_perk_table = user_activity.build_eligable_perks()

        if not eligable_perk_table:
            return True  # Nothing to do

        # Don't need to check for if its enabled, because above func won't include guilds with it disabled.
        for guild_id in eligable_perk_table:
            guild = eligable_perk_table[guild_id]
            ua = user_activity(guild_id)
            for user_id in guild:

                user = guild[user_id]
                give_role = user['give_role']
                take_role = user['take_role']

                # TODO: Make this not alert more than once for a guild.
                if take_role is not None:
                    try:
                        await botapp.rest.remove_role_from_member(
                            guild=guild_id,
                            user=user_id,
                            role=take_role,
                            reason="User did not send a specific amount of messages in 7 days, which made them lose eligability for this role."
                        )

                        # If given no role and only taken, then they have no perk role.
                        if give_role is None:
                            ua.set_last_given_role(role_id=None, user_id=user_id)
                    except hikari.ForbiddenError:
                        await server_logs(guild_id).create_entry(
                            hikari.Embed(
                                title="Activity Perks Error",
                                description=f"We don't have permission to assign the role <@&{give_role}> to users!",
                                colour=0xff0000
                            )
                            .add_field(
                                name="Perk Deleted",
                                value="The perk has been deleted as it cannot be carried out, please re-create it when the problem is solved."
                            )
                        )

                        try:
                            ua.remove_role_perk(give_role)
                        except ua.errors.perk_not_found:
                            pass
                    except hikari.NotFoundError as err:
                        errmsg = err.message.lower()
                        if "role" in errmsg:
                            await server_logs(guild_id).create_entry(
                                hikari.Embed(
                                    title="Activity Perk 404!",
                                    description=f"The role <@&{give_role}> does not exist anymore.",
                                    colour=0xff0000
                                )
                                .add_field(
                                    name="Perk Deleted",
                                    value="The perk has been deleted as it cannot be carried out, please re-create it when the problem is solved."
                                )
                            )

                            try:
                                ua.remove_role_perk(give_role)
                            except ua.errors.perk_not_found:
                                pass  # handles an edge-case or two, users may delete the role while the scan is being done.

                if give_role is not None:
                    try:
                        await botapp.rest.add_role_to_member(
                            guild=guild_id,
                            user=user_id,
                            role=give_role,
                            reason="User sent a specific amount of messages in 7 days, which made them eligable to get this role."
                        )
                        ua.set_last_given_role(role_id=give_role, user_id=user_id)
                    except hikari.ForbiddenError:
                        await server_logs(guild_id).create_entry(
                            hikari.Embed(
                                title="Activity Perks Error",
                                description=f"We don't have permission to assign the role <@&{give_role}> to users!",
                                colour=0xff0000
                            )
                            .add_field(
                                name="Perk Deleted",
                                value="The perk has been deleted as it cannot be carried out, please re-create it when the problem is solved."
                            )
                        )

                        try:
                            ua.remove_role_perk(give_role)
                        except ua.errors.perk_not_found:
                            pass  # handles an edge-case or two, users may delete the role while the scan is being done.
                    except hikari.NotFoundError as err:
                        errmsg = err.message.lower()
                        if "role" in errmsg:
                            await server_logs(guild_id).create_entry(
                                hikari.Embed(
                                    title="Activity Perk 404!",
                                    description=f"The role <@&{give_role}> does not exist anymore.",
                                    colour=0xff0000
                                )
                                .add_field(
                                    name="Perk Deleted",
                                    value="The perk has been deleted as it cannot be carried out, please re-create it when the problem is solved."
                                )
                            )
                            
                            try:
                                ua.remove_role_perk(give_role)
                            except ua.errors.perk_not_found:
                                pass

        return True

    @staticmethod
    def count_all_messages():
        """
        Groups users by guild and shows how many messages they've sent in each guild. Returns a dict like: 
        {guild_id: {user_id: message_count, other_user_id: message_count}, guild_id: {...}, }.

        A user may show up more than once in each dict.
        """
        with get_session() as session:
            records = (
                session.query(observation_entry)
                .filter(observation_entry.timestamp > (datetime.now(timezone.utc) - timedelta(days=activity_days_threshold)))
                .all()
            )

        # Its {guild_id: {user_id: message_count, other_user_id: message_count}}
        user_msg_counts: dict[int: dict[int, int]] = {}

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

        return user_msg_counts

    @staticmethod
    def build_eligable_perks() -> dict[int: dict[int: dict[str: int, str: int]]]:
        """
        Builds a list of each user and what role they should be given in each guild.
        The list looks like this:

        {guild_id1: {user_id1: {"give_role": role_id|None, "take_role": role_id|None}, user_id2: {...}}, guild_id2: {...}}
        """
        user_msg_counts = user_activity.count_all_messages()

        eligable_perk_table: dict[int: dict[int: dict[str: int, str: int]]] = {}
        for guild_id in user_msg_counts:

            is_enabled = user_activity(guild_id).get_guild_enabled()
            if not is_enabled:
                continue  # Don't apply perks to servers with this disabled.

            guild = user_msg_counts[guild_id]
            eligable_perk_table[guild_id] = {}
            ua = user_activity(guild_id)

            for user_id, msg_count in guild.items():
                try:
                    eligable_perk = ua.get_best_perk_for_count(msg_count)
                except user_activity.errors.perk_not_found:
                    role_to_take = ua.get_last_given_role(user_id)  # a role ID or None
                    eligable_perk_table[guild_id][user_id] = {
                        "give_role": None,
                        "take_role": role_to_take,
                    }
                    continue

                leveling = guild_leveling(guild_id)
                leveling_perk = leveling.get_guild_perk_by_role(eligable_perk.role_id)
                is_leveling_perk = (
                    leveling_perk is not None
                    and
                    leveling.get_enabled() is True
                )
                if is_leveling_perk:
                    user_level = leveling.estimate_user_level(user_id)
                else:
                    user_level = None

                last_given_role = ua.get_last_given_role(user_id)

                role_to_give = None
                role_to_take = None
                if last_given_role is None:
                    if eligable_perk:
                        # If its a leveling perk, obey those conditions.
                        if is_leveling_perk:
                            # User was never given an activity perk before, give first perk.
                            if user_level >= leveling_perk.level_needed:
                                role_to_give = eligable_perk.role_id
                            else:
                                role_to_give = None
                        else:
                            role_to_give = eligable_perk.role_id
                    else:
                        role_to_give = None
                    role_to_take = None
                else:
                    if eligable_perk:
                        # User eligable for a perk, figure out which role to take and which one to give if necessary.
                        if last_given_role.given_role == eligable_perk.role_id:
                            # The last given role is equal to the eligable perk, so no changes are needed
                            # As that's the role they should already have.
                            role_to_give = None
                            role_to_take = None
                        else:
                            # Their perk has changed, so take the old perk, give them the new one.
                            if is_leveling_perk:
                                if user_level >= leveling_perk.level_needed:
                                    role_to_give = eligable_perk.role_id
                                    role_to_take = last_given_role.given_role
                                else:
                                    role_to_give = None
                                    role_to_take = None
                            else:
                                role_to_give = eligable_perk.role_id
                                role_to_take = last_given_role.given_role
                    else:
                        # User not eligable for any perks.
                        role_to_give = None
                        role_to_take = last_given_role.given_role

                eligable_perk_table[guild_id][user_id] = {
                    "give_role": role_to_give,  # Either only ever not None if either is True.
                    "take_role": role_to_take,
                }

        return eligable_perk_table

    def _load_perks(self) -> list[guild_activitiy_role_perk]:
        """All perks for this guild, cached. Caller must not mutate the returned list."""
        if (hit := guild_perks_by_guild_cache.get(self.guild_id)) is not None:
            return hit
        with get_session() as session:
            perks = (
                session.query(guild_activitiy_role_perk)
                .filter(guild_activitiy_role_perk.guild_id == self.guild_id)
                .all()
            )
        guild_perks_by_guild_cache[self.guild_id] = perks
        return perks

    def get_best_perk_for_count(self, msg_count: int) -> guild_activitiy_role_perk:
        with get_session() as session:
            perks = (
                session.query(guild_activitiy_role_perk)
                .filter(guild_activitiy_role_perk.guild_id == self.guild_id)
                .all()
            )

        best = min(
            (p for p in perks if _perk_matches(p, msg_count)),
            key=lambda p: (abs(p.msgs_required - msg_count), -p.msgs_required),
            default=None,
        )
        if best is None:
            raise user_activity.errors.perk_not_found()
        return best

    def set_last_given_role(self, role_id:int|None, user_id:int):
        with get_session() as session:
            record = (
                session.query(guild_activitiy_perks_given)
                .filter(guild_activitiy_perks_given.guild_id == self.guild_id)
                .filter(guild_activitiy_perks_given.user_id == user_id)
                .one_or_none()
            )
            if not record:
                record = guild_activitiy_perks_given(
                    guild_id=self.guild_id,
                    user_id=user_id,
                    given_role=role_id
                )
                session.add(record)
            else:
                record.given_role = role_id
            session.commit()
        return True

    def get_last_given_role(self, user_id:int) -> guild_activitiy_perks_given:
        """
        Gets the last role we gave this person.
        """
        with get_session() as session:
            record = (
                session.query(guild_activitiy_perks_given)
                .filter(guild_activitiy_perks_given.guild_id == self.guild_id)
                .filter(guild_activitiy_perks_given.user_id == user_id)
                .one_or_none()
            )

        # If they have None role, and it asks if they have None role, it'll return true.
        return record

    def get_role_perk(self, role_id: int) -> guild_activitiy_role_perk:
        if (hit := guild_perks_roleid_cache.get(role_id)) is not None:
            return hit

        with get_session() as session:
            record = (
                session.query(guild_activitiy_role_perk)
                .filter(guild_activitiy_role_perk.guild_id == self.guild_id)
                .filter(guild_activitiy_role_perk.role_id == role_id)
                .one_or_none()
            )
            if not record:
                raise user_activity.errors.perk_not_found()

            guild_perks_roleid_cache[role_id] = record
            return record

    def remove_role_perk(self, role_id:int):
        with get_session() as session:
            record = (
                session.query(guild_activitiy_role_perk)
                .filter(guild_activitiy_role_perk.guild_id == self.guild_id)
                .filter(guild_activitiy_role_perk.role_id == role_id)
                .one_or_none()
            )
            if not record:
                raise user_activity.errors.perk_not_found()

            guild_perks_roleid_cache.pop(role_id, None)
            guild_perks_by_guild_cache.pop(self.guild_id, None)

            session.delete(record)
            session.commit()
            
        return True

    def add_role_perk(self, role_id:int, msgs_required:int, operator:str="GTE"):
        if not operator in ["GTE", "LTE", "GT", "LT"]:
            raise ValueError(f"{operator} is an incorrect operator type.")
        with get_session() as session:
            record = (
                session.query(guild_activitiy_role_perk)
                .filter(guild_activitiy_role_perk.guild_id == self.guild_id)
                .filter(guild_activitiy_role_perk.role_id == role_id)
                .one_or_none()
            )
            if record:
                raise user_activity.errors.perk_exists(record)

            guild_perks_by_guild_cache.pop(self.guild_id, None)
            record = guild_activitiy_role_perk(
                guild_id=self.guild_id,
                role_id=role_id,
                msgs_required=msgs_required,
                operator=operator
            )
            session.add(record)
            session.commit()
        return True

    async def _handle_role_sync_error(
        self,
        guild_id: int,
        role_id: int | None,
        err: Exception,
        ua: "user_activity",
        *,
        guilds_already_warned: list[int],
        guilds_to_be_warned: list[list[int, str]],
    ) -> None:
        """
        Centralised error handling for role add/remove failures during activity scans.
        (It duplicated it 4 times in practice so I put it here for DRY purposes. :P)
        """
        # Only warn once per guild per scan pass.
        already_warned = guild_id in guilds_already_warned

        if isinstance(err, hikari.NotFoundError):
            errlower = err.message.lower()
            if "role" in errlower:
                if not already_warned:
                    guilds_already_warned.append(guild_id)
                    guilds_to_be_warned.append([
                        guild_id,
                        "The active member role does not exist anymore, "
                        "admins should assign a new role.",
                    ])
                ua.set_guild_active_role(None)
                ua.set_guild_enabled(False)
                if role_id is not None:
                    try:
                        ua.remove_role_perk(role_id)
                    except ua.errors.perk_not_found:
                        pass
            elif "user" in errlower or "member" in errlower:
                # Member left / was kicked mid-scan or smth, nothing to do.
                pass
            else:
                logging.warning(
                    "Unhandled NotFoundError during role sync in guild %s: %s",
                    guild_id, err.message,
                )
            return

        if isinstance(err, hikari.ForbiddenError):
            if not already_warned:
                guilds_already_warned.append(guild_id)
                guilds_to_be_warned.append([
                    guild_id,
                    f"We can't give or take the <@&{role_id}> role to users as "
                    f"we don't have sufficient permissions.",
                ])
            ua.set_guild_enabled(False)
            if role_id is not None:
                try:
                    ua.remove_role_perk(role_id)
                except ua.errors.perk_not_found:
                    pass
            return

        # Unknown exception type, we re-raise so it isn't silenced.
        raise err

    @staticmethod
    async def scan_users_active():
        """
        Gets and applies the changes to each guild for each user. Can take a while to execute.
        """
        result = user_activity.determine_active()
        newly_active = result['newly_active']
        no_longer_active = result['no_longer_active']

        guilds_to_be_warned: list[list[int, str]] = []
        guilds_tbw_id_list = []

        for guild_id, user_id in newly_active:
            ua = user_activity(guild_id)
            if not ua.get_guild_enabled():
                continue
            role_id = ua.get_guild_active_role()
            try:
                await botapp.rest.add_role_to_member(
                    guild=guild_id,
                    user=user_id,
                    role=role_id,
                    reason="User was flagged as being active in the community.",
                )
            except (hikari.NotFoundError, hikari.ForbiddenError) as err:
                await ua._handle_role_sync_error(
                    guild_id, role_id, err, ua,
                    guilds_already_warned=guilds_tbw_id_list,
                    guilds_to_be_warned=guilds_to_be_warned,
                )

        for guild_id, user_id in no_longer_active:
            ua = user_activity(guild_id)
            if not ua.get_guild_enabled():
                continue
            role_id = ua.get_guild_active_role()
            if not role_id:
                continue
            try:
                await botapp.rest.remove_role_from_member(
                    guild=guild_id,
                    user=user_id,
                    role=role_id,
                    reason="User was flagged as no longer being active in the community.",
                )
            except (hikari.NotFoundError, hikari.ForbiddenError) as err:
                await ua._handle_role_sync_error(
                    guild_id, role_id, err, ua,
                    guilds_already_warned=guilds_tbw_id_list,
                    guilds_to_be_warned=guilds_to_be_warned,
                )

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
                guild_activity_enabled_cache[self.guild_id] = False
                return False
            guild_activity_enabled_cache[self.guild_id] = record.enabled
            return record.enabled

    def set_guild_enabled(self, enabled:bool):
        if guild_activity_enabled_cache.get(self.guild_id) is not None:
            guild_activity_enabled_cache.pop(self.guild_id, None)
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

        guild_activity_enabled_cache[self.guild_id] = enabled
        return True

    def get_guild_active_role(self) -> int:
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

    def set_guild_active_role(self, role_id:int|None) -> bool:
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
            guild_active_role_cache[self.guild_id] = role_id
        return True

    def get(self, user_id:int) -> UserActivitySnapshot:
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

            constructed_class = UserActivitySnapshot(
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
            else:
                activity_rec.is_active = is_active

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
                .filter(observation_entry.guild_id == self.guild_id)
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

        user_msg_counts = user_activity.count_all_messages()

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
