from library.database.guilds import dbguild, violations
from modules.moderation.group import group
from library.permissions import prechecks
from library.permissions import perms
from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="profile",
    description="Have the bot compile a full profile on a user"
):
    
    target_user = lightbulb.user("user", "Who do we compile data on?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("moderation profile", ctx, hikari.Permissions.MANAGE_MESSAGES)

        # TODO: Make this track if the member ever was muted or banned in the past in the server.

        guild = dbguild(ctx.guild_id)
        all_violations = violations.get_violations_by_offender(self.target_user.id)
        all_warnings = guild.warnings.get_by_user(self.target_user.id)
        automod_violations_count = len([violation for violation in all_violations if violation.automated == True])
        violations_appealed = len([violation for violation in all_violations if violation.appealed == True])
        warnings_automated = len([warning for warning in all_warnings if warning.moderator_id == ds.d["myid"]])
        
        target_user = await ctx.client.rest.fetch_member(ctx.guild_id, self.target_user.id)
        user_perms = await perms.get_user_permissions(ctx.guild_id, self.target_user.id)
        if hikari.Permissions.ADMINISTRATOR in user_perms:
            member_status = "**ADMIN**"
        elif hikari.Permissions.MANAGE_MESSAGES in user_perms:
            member_status = "*MODERATOR*"
        else:
            member_status = "MEMBER"

        if automod_violations_count != 0:
            auto_violation_ratio = round((automod_violations_count / len(all_violations)) * 100, 2)
            manual_violation_ratio = 100 - auto_violation_ratio
        else:
            auto_violation_ratio = 0
            manual_violation_ratio = 0

        text_count = 0
        spam_count = 0
        image_count = 0
        for v in all_violations:
            if v.automated != True:
                continue

            if v.whistleblower == "Spam Filter":
                spam_count += 1
            elif v.whistleblower == "Image Filter":
                image_count += 1
            elif v.whistleblower in ["equality", "symbol", "collapse", "spacehack", "stitching", "reversing", "similarity", "syntactic"]:
                text_count += 1
            else:
                continue

        embed = (
            hikari.Embed(
                title=f"User {self.target_user.display_name} Profile",
                description=(
                    f"{len(all_warnings)} Warnings • {automod_violations_count}x Automod Flags • {member_status}\n"
                    f"Joined at {target_user.joined_at.strftime("%d-%m-%Y")} | Joined Discord on {target_user.created_at.strftime("%d-%m-%Y")}"
                ),
                colour=0xff0000
            )
            .add_field(
                name=f"{len(all_violations)}x Violations",
                value=(
                    f"This user has been involved in {len(all_violations)} Violations discord-wide,\n{automod_violations_count} of which were Automated.\n\n"
                    f"This gives a ratio of {auto_violation_ratio}% automatic flags from the automoderation system, "
                    f"and {manual_violation_ratio}% from violations given by server admins. {violations_appealed}x Violations were appealed as not-guilty.\n\n"
                    f"**{spam_count}x counts of Spam • {text_count} Counts of Text-Violations • {image_count} Flagged Images.**"
                )
            )
            .add_field(
                name=f"{len(all_warnings)}x Warnings",
                value=(
                    f"User has received {len(all_warnings)}x Warnings from moderators or the automoderation system. "
                    f"Of these warnings, {warnings_automated} were automated, "
                    f"leaving {len(all_warnings) - warnings_automated} warnings from humans."
                )
            )
            .set_thumbnail(hikari.URL(target_user.make_guild_avatar_url(), "user_pfp.png"))
        )

        user_mute = guild.muting.get_mute(target_user.id)
        if user_mute:
            if user_mute.active:
                scheduled_unmute = f"is scheduled for <t:{int(user_mute.scheduled_unmute)}:f>" if user_mute.scheduled_unmute != -1 else "is not scheduled"
                embed.add_field(
                    name="Member Muted",
                    value=f"User was muted for reason: \"{user_mute.reason}\"\n\nTheir unmute {scheduled_unmute}."
                )

        user_ban = guild.bans.fetch_ban(target_user.id)
        if user_ban:
            if user_ban.active:
                # TODO: Verify if this code actually works
                scheduled_unban = user_ban.time_to_unban.strftime("%d-%m-%Y")
                embed.add_field(
                    name="User Banned",
                    value=f"User is currently banned for reason: \"{user_ban.reason}\"\n\nTheir unban is scheduled for {scheduled_unban}"
                )

        await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)