from library.database.guilds import violations, user_notes, dbguild
from library.botapp import miru_client
from library.permissions import perms
from library import datastore as ds
from library import settings
import hikari
import miru


class views:
    def __init__(self, author_id:int, guild_id:int, target_user:hikari.Member):
        self.author_id = author_id
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.target_user = target_user
        self.member_status = None
        self.note_count = len(user_notes(target_user.id, guild_id).get_all())

    async def gen_embed(self):
        all_violations = violations.get_violations_by_offender(self.target_user.id)
        all_warnings = self.guild.warnings.get_by_user(self.target_user.id)
        automod_violations_count = len([violation for violation in all_violations if violation.automated == True])
        violations_appealed = len([violation for violation in all_violations if violation.appealed == True])
        warnings_automated = len([warning for warning in all_warnings if warning.moderator_id == ds.d["myid"]])
        last_10_warnings = [str(warning.warn_id) for warning in all_warnings[-10:]]

        if not self.member_status:
            user_perms = await perms.get_user_permissions(self.guild_id, self.target_user.id)
            if hikari.Permissions.ADMINISTRATOR & user_perms:
                self.member_status = "**ADMIN**"
            elif hikari.Permissions.MANAGE_MESSAGES & user_perms:
                self.member_status = "*MODERATOR*"
            elif hikari.Permissions.MANAGE_MESSAGES & user_perms:
                self.member_status = "MEMBER"
            else:
                self.member_status = "Not in server"

        is_maintainer = self.target_user.id == settings.get.primary_maintainer()

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

        in_guild = True  # Assumes they're in a guild we're in.
        try:
            joined_server_text = self.target_user.joined_at.strftime('%d-%m-%Y')
        except AttributeError: 
            in_guild = False
            joined_server_text = "N/A"

        # TODO: Make this show user activity in a community too. (If possible) 
        embed = (
            hikari.Embed(
                title=f"User Profile: {self.target_user.display_name}",
                description=(
                    f"{len(all_warnings)} warnings • "
                    f"{automod_violations_count} automated flags • "
                    f"{self.member_status}\n{"__Primary Bot Maintainer__\n\n" if is_maintainer else ""}"
                    f"Joined server: {joined_server_text} • "
                    f"Discord account created: {self.target_user.created_at.strftime('%d-%m-%Y')}"
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
                    f"Latest warnings by ID:\n"
                    f"`{', '.join(last_10_warnings) if last_10_warnings else 'No warnings on record.'}`"
                )
            )
        )

        if in_guild:
            embed.set_thumbnail(
                hikari.URL(self.target_user.make_guild_avatar_url(), "user_pfp.png")
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

        user_mute = self.guild.muting.get_mute(self.target_user.id)
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

        user_ban = self.guild.bans.fetch_ban(self.target_user.id)
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
                embed = await viewself.gen_embed()
                await viewself.ctx.edit_response(
                    viewself.resp,
                    embed=embed,
                    components=[]
                )
                self.stop()

            if viewself.guild.bans.fetch_ban(user_id=viewself.target_user.id) is None:
                @miru.button(
                    label="Ban",
                    style=hikari.ButtonStyle.SECONDARY,
                    emoji="🔨"
                )
                async def ban_user(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if not ctx.user.id == viewself.author_id:
                        return
                    
                    # Returns the user to the original view
                    from modules.moderation.views.profile_subviews.confirm_ban_view import views as confirm_view
                    view = confirm_view(
                        author_id=viewself.author_id,
                        guild_id=viewself.guild_id,
                        target_user=viewself.target_user,
                    )
                    embed = await view.gen_embed()
                    view_menu = view.init_view()

                    await ctx.edit_response(
                        embed=embed,
                        components=view_menu.build(),
                        flags=hikari.MessageFlag.EPHEMERAL
                    )

                    miru_client.start_view(view_menu)
                    await view_menu.wait()
                    self.stop()
            else:
                @miru.button(
                    label="Unban",
                    style=hikari.ButtonStyle.SECONDARY,
                    emoji="🔨"
                )
                async def unban_user(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if not ctx.user.id == viewself.author_id:
                        return
                    
                    # Returns the user to the original view
                    embed = await viewself.gen_embed()
                    # TODO: Update this to use its own view that asks for the reason.
                    unban_attempt_ok = await viewself.guild.bans.unban_user(
                        viewself.target_user.id, viewself.author_id, reason="No reason provided."
                    )
                    if unban_attempt_ok:
                        embed.add_field(
                            name="User Unban",
                            value="This user's ban was revoked, and can rejoin at any time now."
                        )
                    else:
                        embed.add_field(
                            name="Unban Failed",
                            value="An error occured trying to unban this user, do we have sufficient permissions?"
                        )

                    await ctx.edit_response(
                        embed=embed,
                        flags=hikari.MessageFlag.EPHEMERAL
                    )

            if viewself.note_count != 0:
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
                        viewself.note_count -= 1
                    else:
                        embed.add_field(
                            name="Failed to delete",
                            value="We were unable to delete that note for this user."
                        )
                    await ctx.edit_response(embed)

            @miru.button(
                label="Append Note",
                style=hikari.ButtonStyle.SECONDARY,
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
                            success = notes.add(f"{self.usernote.value} - <@{ctx.author.id}>")
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
                            viewself.note_count += 1
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