from library import datastore as ds
from library.botapp import botapp
import lightbulb
import hikari

class perms:
    class embeds:
        def forbidden():
            return hikari.Embed(
                title="Forbidden",
                description="You're missing the required permissions to run this command."
            )

    class errors:
        class user_perm_error(Exception):
            def __init__(self):
                super().__init__("User does not have required permissions.")
            def __str__(self):
                return "User does not have required permissions."

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