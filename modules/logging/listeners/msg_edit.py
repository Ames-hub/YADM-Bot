from library.database.auditing import logs_config, server_logs
from difflib import SequenceMatcher
import lightbulb
import hikari

loader = lightbulb.Loader()

def highlight_changes(original: str, changed: str) -> str:
    matcher = SequenceMatcher(None, original, changed)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append(changed[j1:j2])
        else:
            result.append(f"**__{changed[j1:j2]}__**")

    return "".join(result)

@loader.listener(hikari.GuildMessageUpdateEvent)
async def botfunction(event: hikari.GuildMessageUpdateEvent):
    if event.member.is_bot:
        return
    if not event.old_message.content:  # might be missing from cache
        return

    logs = logs_config(event.guild_id)
    if not logs.msg_edits.get_do_logging():
        return

    embed = (
        hikari.Embed(
            title="Message Edit",
            description=f"{event.member.mention} just editted [their message.]({event.message.make_link(event.guild_id)})",
            colour=0x0000ff
        )
        .add_field(
            name="New Message",
            value=f"\"{event.message.content}\"",
            inline=True
        )
        .add_field(
            name="Old Message",
            value=f"\"{event.old_message.content}\"",
            inline=True
        )
    )

    if event.old_message.content != event.message.content:
        embed.add_field(
            name="Difference",
            value=f"{highlight_changes(event.old_message.content, event.message.content)}"
        )
        embed.set_footer("Difference shown in the highlighted and underlined text")
    else:
        embed.set_footer("There is no text difference in the message, only attachments have changed.")
    
    attached = None
    if len(event.old_message.attachments) > len(event.message.attachments):
        embed.add_field(
            name="Attachment Deleted",
            value="This user deleted the following attachments that are attached."
        )
        old_files = [e.filename for e in event.old_message.attachments]
        new_files = [e.filename for e in event.message.attachments]
        for of in old_files:
            if of not in new_files:
                # This is the deleted one
                for file in event.old_message.attachments:
                    if file.filename == of and str(file.extension).lower() in ['png', 'jpeg', 'gif', "tiff", "bmp", "jpg"]:
                        attached = [file]

    elif len(event.old_message.attachments) != len(event.message.attachments):
        embed.add_field(
            name="Attachments",
            value="We've detected that the embed attachments have changed, the current attachments are attached."
        )
        attached = event.message.attachments

    await server_logs(event.guild_id).create_entry(embed, attachments=attached)