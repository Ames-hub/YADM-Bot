from library.database.guilds import dbguild, server_logs
from library import datastore as ds
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

common_mod_roles = ['moderator', 'mod', 'judge', 'diplomat', 'trust and safety team']
mod_perms = hikari.Permissions.MANAGE_MESSAGES + hikari.Permissions.MUTE_MEMBERS

@loader.task(lightbulb.uniformtrigger(hours=4, wait_first=False), auto_start=True)
async def scan_for_modrole() -> None: 
    guild_id_list = ds.d["modrole-scanner-queue"]
    for guild_id in guild_id_list:
        ds.d["modrole-scanner-queue"].remove(guild_id)
        guild = dbguild(guild_id)

        # Make sure we're only scanning for guilds with no mod role
        mod_role = guild.get.mod_role_id()
        if mod_role is not None:
            continue

        guild_roles = await botapp.rest.fetch_roles(guild_id)

        # Attempts to determine which role might be the guild's mod role
        mod_flags_list = []
        for role in guild_roles:
            mod_flags_count = 0
            if role.name.lower() in common_mod_roles:
                # Role name is fitting of a mod
                mod_flags_count += 1

            if (role.permissions & mod_perms) > 0:
                # Permissions fitting of a mod
                mod_flags_count += 1

            if role.is_premium_subscriber_role or role.is_available_for_purchase:
                # No way in hell this is a mod role.
                mod_flags_count -= 2

            mod_flags_list.append((role.id, mod_flags_count))

        # Picks the role with the highest flag int
        mod_role_winner = None
        cur_highest = 0
        for item in mod_flags_list:
            role_id = item[0]
            flags_count = item[1]
            if flags_count == 0:
                continue  # Don't even count it.

            if cur_highest < flags_count:
                mod_role_winner = role_id

        await server_logs(guild_id).create_entry(
            hikari.Embed(
                title="Mod Role Auto-detected",
                description=(
                    "We detected that no mod role is present for your server, "
                    f"so we looked at your roles and detected <@&{role_id}> as your moderator role!"
                ),
                colour=0x00ff00
            )
        )
        guild.set.mod_role_id(mod_role_winner)