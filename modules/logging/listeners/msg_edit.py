from library.database.auditing import logs_config, server_logs
from difflib import SequenceMatcher
import lightbulb
import hikari

loader = lightbulb.Loader()

def highlight_changes(original: str, changed: str) -> str:
    # First compare the messages as words.
    old_words = original.split()
    new_words = changed.split()

    word_matcher = SequenceMatcher(None, old_words, new_words)
    result = []

    for tag, i1, i2, j1, j2 in word_matcher.get_opcodes():
        if tag == "equal":
            result.extend(new_words[j1:j2])
            continue

        if tag == "replace":
            old_chunk = old_words[i1:i2]
            new_chunk = new_words[j1:j2]

            # If this is a single word changing into another single word,
            # do a character-level comparison.
            if len(old_chunk) == 1 and len(new_chunk) == 1:
                old_word = old_chunk[0]
                new_word = new_chunk[0]

                char_matcher = SequenceMatcher(
                    None,
                    old_word,
                    new_word
                )

                changed_word = []

                for char_tag, ci1, ci2, cj1, cj2 in char_matcher.get_opcodes():
                    if char_tag == "equal":
                        changed_word.append(new_word[cj1:cj2])
                    else:
                        changed_word.append(
                            f"**__{new_word[cj1:cj2]}__**"
                        )

                result.append("".join(changed_word))

            else:
                # Multiple words were replaced, so highlight the
                # entire new section.
                result.extend(
                    f"**__{word}__**"
                    for word in new_chunk
                )

        elif tag == "insert":
            result.extend(
                f"**__{word}__**"
                for word in new_words[j1:j2]
            )

        elif tag == "delete":
            # Deleted text isn't in the new message, so there's
            # nothing to display here.
            continue

    return " ".join(result)

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
            description=f"{event.member.mention} just editted [their message.]({event.message.make_link(event.guild_id)}) in <#{event.channel_id}>",
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