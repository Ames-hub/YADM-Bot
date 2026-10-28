from library.database.guilds import dbguild, violations, user_notes
from library.botapp import botapp, miru_client
from library.permissions import perms
from library import datastore as ds
import hikari
import miru


class views:
    def __init__(self, author_id:int, guild_id:int, target_user:hikari.Member):
        self.author_id = author_id
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.target_user = target_user

    async def gen_embed(self):
        all_violations = violations.get_violations_by_offender(self.target_user.id)
        all_warnings = self.guild.warnings.get_by_user(self.target_user.id)
        automod_violations_count = len([violation for violation in all_violations if violation.automated == True])
        violations_appealed = len([violation for violation in all_violations if violation.appealed == True])
        warnings_automated = len([warning for warning in all_warnings if warning.moderator_id == ds.d["myid"]])
        last_10_warnings = [str(warning.warn_id) for warning in all_warnings[-10:]]

        target_user = await botapp.rest.fetch_member(self.guild_id, self.target_user.id)
        user_perms = await perms.get_user_permissions(self.guild_id, self.target_user.id)
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
                title=f"User Profile: {self.target_user.display_name}",
                description=(
                    f"{len(all_warnings)} warnings • "
                    f"{automod_violations_count} automated flags • "
                    f"{member_status}\n"
                    f"Joined server: {target_user.joined_at.strftime('%d-%m-%Y')} • "
                    f"Discord account created: {target_user.created_at.strftime('%d-%m-%Y')}"
                ),
                colour=0xff0000
            )
            .add_field(
                name=f"Violations ({len(all_violations)})",
                value=(
                    f"Automated: {automod_violations_count} ({auto_violation_ratio}%)\n"
                    f"Manual: {len(all_violations) - automod_violations_count} ({manual_violation_ratio}%)\n"
                    f"Appealed as not guilty: {violations_appealed}\n\n"
                    f"Spam: {spam_count} • "
                    f"Text violations: {text_count} • "
                    f"Flagged images: {image_count}"
                )
            )
            .add_field(
                name=f"Warnings ({len(all_warnings)})",
                value=(
                    f"Automated: {warnings_automated}\n"
                    f"Manual: {len(all_warnings) - warnings_automated}\n"
                    f"Latest warnings by ID:\n`{", ".join(last_10_warnings)}`"
                )
            )
            .set_thumbnail(
                hikari.URL(target_user.make_guild_avatar_url(), "user_pfp.png")
            )
        )

        notes = user_notes(self.target_user.id, self.guild_id)
        all_notes = notes.get_all()

        note_text = [
            f"**#{note.identifier}** | {note.text}"
            for note in all_notes
        ]

        embed.add_field(
            name=f"Moderator Notes ({len(all_notes)})",
            value="\n".join(note_text) if note_text else "No moderator notes."
        )

        user_mute = self.guild.muting.get_mute(target_user.id)
        if user_mute and user_mute.active:
            scheduled_unmute = (
                f"<t:{int(user_mute.scheduled_unmute)}:f>"
                if user_mute.scheduled_unmute != -1
                else "Not scheduled"
            )

            embed.add_field(
                name="Active Mute",
                value=(
                    f"Reason: {user_mute.reason}\n"
                    f"Scheduled unmute: {scheduled_unmute}"
                )
            )

        user_ban = self.guild.bans.fetch_ban(target_user.id)
        if user_ban and user_ban.active:
            scheduled_unban = (
                user_ban.time_to_unban.strftime("%d-%m-%Y")
                if user_ban.time_to_unban
                else "Not scheduled"
            )

            embed.add_field(
                name="Active Ban",
                value=(
                    f"Reason: {user_ban.reason}\n"
                    f"Scheduled unban: {scheduled_unban}"
                )
            )

        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            async def on_timeout(self) -> None:
                self.message.components = []
                self.stop()

            @miru.text_select(
                placeholder="Delete Note",
                options=[
                    miru.SelectOption(label=f"Note #{note.identifier}")
                    for note in user_notes(viewself.target_user.id, viewself.guild_id).get_all()
                ],
            )
            async def get_note_to_delete(self, ctx: miru.ViewContext, select: miru.TextSelect) -> None:
                if not ctx.user.id == viewself.author_id:
                    return
                if ds.d["high_ping"]:
                    # High ping logic
                    await ctx.defer()
                
                note_id = int(select.values[0].split("#")[1])  # Get all text after the hash
                notes = user_notes(viewself.author_id, ctx.guild_id)
                try:
                    success = notes.remove(note_id)
                except notes.errors.notenotfound:
                    embed = await viewself.gen_embed()
                    embed.add_field(
                        name="Can't find note",
                        value="It seems that note was already deleted by someone else?"
                    )
                    await ctx.edit_response(embed)
                    return

                embed = await viewself.gen_embed()
                if success:
                    embed.add_field(
                        name="Note Deleted",
                        value="**This note has been deleted from the user's profile**"
                    )
                else:
                    embed.add_field(
                        name="Failed to delete",
                        value="We were unable to delete that note for this user."
                    )
                await ctx.edit_response(embed)

            @miru.button(
                label="Append Note",
                style=hikari.ButtonStyle.DANGER,
                emoji="🗒️"
            )
            async def add_note(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                class MyModal(miru.Modal, title="Create User Note"):
                    usernote = miru.TextInput(
                        label="Note Content",
                        placeholder="What is there that needs to be known?",
                        required=True,
                        max_length=256,
                        min_length=10,
                        style=hikari.TextInputStyle.PARAGRAPH,
                    )

                    # The callback function is called after the user hits 'Submit'
                    async def callback(self, ctx: miru.ModalContext) -> None:
                        if not ctx.user.id == viewself.author_id:
                            return
                        if ds.d["high_ping"]:
                            # High ping logic
                            await ctx.defer()

                        notes = user_notes(viewself.author_id, ctx.guild_id)
                        try:
                            success = notes.add(self.usernote.value)
                        except notes.errors.toomanynotes:
                            embed = await viewself.gen_embed()
                            embed.add_field(
                                name="Too many notes",
                                value=f"Cannot add that note; you can only have a total of {notes.note_limit} notes per profile."
                            )
                            await ctx.edit_response(embed)
                            return
                        
                        embed = await viewself.gen_embed()
                        if success:
                            embed.add_field(
                                name="Note Added",
                                value="**This note has been added to the user's account**"
                            )
                        else:
                            embed.add_field(
                                name="Failed to add",
                                value="We were unable to add the note for this user."
                            )
                        await ctx.edit_response(embed)

                modal = MyModal()
                builder = modal.build_response(miru_client)
                await builder.create_modal_response(ctx.interaction)
                miru_client.start_modal(modal)

        return Menu_Init()