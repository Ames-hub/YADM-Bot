from library import datastore as ds
from library.botapp import botapp
from library.settings import get
from datetime import datetime
import lightbulb
import hikari

async def prechecks(
        cmd_name:str,
        ctx:lightbulb.Context,
        permission:hikari.Permissions|None = None,
        cooldown_s:int|None = None,
        bot_admin_only:bool=False,
        auto_defer=True,
    ):
    """
    Docstring for prechecks
    
    :param cmd_name: A Unique identifier to give a command.
    :type cmd_name: str
    :param permission: The permission required to run the command. Enter as None if not required.
    :type permission: hikari.Permissions | None
    :param ctx: The command context
    :type ctx: lightbulb.Context
    :param cooldown_s: How many seconds can pass before use of the command is allowed again
    :type cooldown_s: int | None
    :param bot_admin_only: If the command is only for bot admins.
    :type bot_admin_only: bool
    :param auto_defer: Should we defer on high-ping?
    type auto_defer: bool
    """
    # High Latency behavior
    if botapp.heartbeat_latency * 1000 > 300 and auto_defer:  # ms
        await ctx.defer()

    guild_id = ctx.guild_id
    user_id = ctx.user.id

    if not bot_admin_only:
        if permission is not None:
            if await perms.is_privileged(permission, guild_id, user_id) is False:
                await ctx.respond(perms.embeds.forbidden())
                raise perms.errors.user_perm_error
    else:
        allowed = ctx.user.id == get.primary_maintainer()
        if allowed:
            return True

    if cooldown_s is not None:
        cd = cooldowns(ctx.user.id)
        wait_time = cd.cmd_cooled(cmd_name)
        if not wait_time == True:
            await ctx.respond(perms.embeds.cooldown_active(wait_time))
            raise perms.errors.cooldown_active

        ds.d["cmd_cooldowns_memory"][cmd_name] = cooldown_s
        cd.start_cooldown(cmd_name, cooldown_s)

class cooldowns:
    def __init__(self, user_id):
        self.user_id = user_id
    
    def start_cooldown(self, cmd_name, cooldown_s):
        if not ds.d['cooldowns'].get(self.user_id, False):
            ds.d['cooldowns'][self.user_id] = {}
        
        cooldown_expiration = datetime.now().timestamp() + cooldown_s

        ds.d['cooldowns'][self.user_id][cmd_name] = cooldown_expiration
        return True
    
    def cmd_cooled(self, cmd_name):
        time_now = datetime.now().timestamp()
        cooldown_over = time_now >= ds.d['cooldowns'][self.user_id][cmd_name]
        if cooldown_over:
            return True
        else:
            return time_now - ds.d['cooldowns'][self.user_id][cmd_name]

class perms:
    class embeds:
        def forbidden():
            return hikari.Embed(
                title="Forbidden",
                description="You're missing the required permissions to run this command."
            )

        def cooldown_active(wait_time):
            if wait_time <= 120:  # Under 2 minutes
                time_unit = "second(s)"
                # No change to wait_time (remains in seconds).
            elif wait_time <= 3599:  # Under an hour
                time_unit = "minute(s)"
                wait_time = wait_time // 60  # Convert seconds to minutes.
            elif wait_time <= 86399:  # Less than a day (under 24 hours)
                time_unit = "hour(s)"
                wait_time = wait_time // 3600  # Convert seconds to hours.
            else:  # Greater than or equal to 1 day
                time_unit = "day(s)"
                wait_time = wait_time // 86400  # Convert seconds to days.

            return hikari.Embed(
                title="❄️ Cooldown ❄️",
                description=f"You still have {wait_time} {time_unit} until you can run this command again."
            )   

    class errors:
        class user_perm_error(Exception):
            def __init__(self):
                super().__init__("User does not have required permissions.")
            def __str__(self):
                return "User does not have required permissions."
        class cooldown_active(Exception):
            def __init__(self):
                pass

    @staticmethod
    async def perms_precheck(permission:hikari.Permissions, ctx:lightbulb.Context):
        """
        Docstring for perms_precheck
        
        :param permission: Description
        :param ctx: Description
        :type ctx: lightbulb.Context
        """
        guild_id = ctx.guild_id
        user_id = ctx.user.id

        if await perms.is_privileged(permission, guild_id, user_id) is False:
            await ctx.respond(perms.embeds.forbidden())
            raise perms.errors.user_perm_error

    @staticmethod
    async def is_privileged(permission, guild_id:int, user_id:int):
        if permission is None:
            return True  # Always permitted if no permission is needed
        if guild_id is None:
            raise ValueError("Guild ID can't be None!")
        if user_id is None:
            raise  ValueError("User ID can't be None!")

        guild_id = int(guild_id)
        user_id = int(user_id)

        user_perms = await perms.get_user_permissions(guild_id, user_id)

        if permission in user_perms:
            return True
        else:
            if hikari.Permissions.ADMINISTRATOR in user_perms:
                return True
            return False

    @staticmethod
    async def get_user_permissions(guild_id, user_id):
        user_id = int(user_id)
        guild_id = int(guild_id)

        member:hikari.Member = await botapp.rest.fetch_member(guild=guild_id, user=user_id)

        # If the user is the owner of the guild, return all permissions.
        owner_id = await perms.get_guild_owner_id(guild_id)

        if owner_id == member.id:
            return [
                # All the major permissions
                hikari.Permissions.ADMINISTRATOR,
                hikari.Permissions.MANAGE_GUILD,
                hikari.Permissions.MANAGE_ROLES,
            ]

        perms_list = []
        roles = await member.fetch_roles()
        for role in roles:
            for perm in role.permissions:
                if perm not in perms_list:
                    perms_list.append(perm)
                else:
                    continue

        return perms_list

    @staticmethod
    async def get_guild_owner_id(guild_id):
        if ds.d['guild_owner_ids_cache'].get(guild_id, None) is None:
            guild = botapp.cache.get_guild(guild_id)
            if guild is not None:
                owner_id = guild.owner_id
            else:
                guild = await botapp.rest.fetch_guild(guild_id)
                owner_id = guild.owner_id
            ds.d['guild_owner_ids_cache'][guild_id] = owner_id
        else:
            owner_id = ds.d['guild_owner_ids_cache'][guild_id]

        return int(owner_id)