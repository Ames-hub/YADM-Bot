from datetime import datetime, timezone, timedelta
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from datetime import datetime, timedelta
from library import automod
import hikari
import miru
import io


class views:
    def __init__(self, guild_id:int, do_kick:bool, do_ban:bool, penalize:bool, channel:int, hours_back:int, mod_id:int):
        self.guild_id = guild_id
        self.do_kick = do_kick
        self.do_ban = do_ban
        self.penalize = penalize
        self.channel = channel
        self.hours_back = hours_back
        self.mod_id = mod_id

    def gen_embed(self):
        desc = (
            f"You are about to begin a retroactive scan of all messages in the channel <#{self.channel}> before "
            f"<t:{int(datetime.now().timestamp() - timedelta(hours=self.hours_back).total_seconds())}:f>.\n"
            "Please confirm if you want to take this action."
        )
        if self.penalize:
            desc += "\n\n**ALL USERS WILL BE RETRO-ACTIVELY PENALISED ACCORDING TO CONTENT POLICY MODERATION SETTINGS RIGHT NOW.**"
        embed = hikari.Embed(
            title="Scan Confirmation",
            description=desc,
            colour=0xff0000
        )
        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if not ctx.author.id == viewself.mod_id:  # Prevnts others from clicking it
                    return
                await ctx.edit_response(
                    hikari.Embed(
                        title="Cancelled",
                        description="Retroscan has been cancelled.",
                    ),
                    components=[]
                )
                self.stop()

            @miru.button(
                label="Confirm",
                style=hikari.ButtonStyle.DANGER,
                emoji="⚠️"
            )
            async def delete(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if not ctx.author.id == viewself.mod_id:  # Prevnts others from clicking it
                    return

                await ctx.respond(
                    hikari.Embed(
                        title="Scanning...",
                        description="This may take a while, please hold tight for a couple minutes!",
                        colour=0xFFA500
                    )
                )

                log_msg = f"<#{viewself.channel}> Is currently undergoing a retro-scan as ordered by {ctx.user.mention}, spanning two weeks backwards from now."
                if viewself.penalize:
                    log_msg += f"\nPenalties are being applied, users will be"
                    log_msg += f"{" banned," if viewself.do_ban else ""}{" and" if viewself.do_ban and viewself.do_kick else ""}{" kicked" if viewself.do_kick else ""}"

                # We cannot delete msgs older than two weeks, so if they're older than that, do not delete.
                do_delete = True
                if viewself.hours_back > 335:
                    do_delete = False

                # Get all messages within the time frame.
                target_time = datetime.now(timezone.utc).timestamp() - timedelta(hours=viewself.hours_back).total_seconds()
                try:
                    fetched_messages = await ctx.client.rest.fetch_messages(viewself.channel, after=target_time)
                except (hikari.ForbiddenError, hikari.UnauthorizedError):
                    await ctx.edit_response(
                        hikari.Embed(
                            title="Bad Bot Permissions",
                            description="We do not have permission to fetch messages that far back.",
                            colour=0xff0000
                        )
                    )
                    return

                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Retroscan",
                        description=log_msg,
                        colour=0xff0000
                    )
                )

                actions_log = []
                noscan_list = []
                for message in fetched_messages:
                    if message.author.is_system or message.author.is_bot:
                        continue
                    if not message.content:
                        continue
                    bad_msg, check_name, flagged_word, _ = automod.text_check(message.content, ctx.guild_id)
                    if bad_msg:
                        msg_link = f"message (link: {message.make_link(message.guild_id)})"
                        if viewself.penalize:
                            if viewself.do_kick or viewself.do_ban:
                                noscan_list.append(message.author.id)  # Do not punish someone after being banned, they're already gone.
                                if do_delete:
                                    try:
                                        await message.delete()
                                    except (hikari.ForbiddenError, hikari.NotFoundError):
                                        continue
                                continue
                            time = int(datetime.now().timestamp() - message.timestamp.timestamp())
                            reason = (
                                f"<t:{time}:R>, user <@{message.author.id}> sent a {msg_link} with the word '||{flagged_word}||', "
                                f"triggering the '{check_name}' check which violates\n"
                                "the new server chat policy, and is being retro-actively punished."
                            )
                            await dbguild(ctx.guild_id).handle_like_guilty(
                                user_id=message.author.id,
                                reason=reason,
                                mod_id=ctx.user.id,
                                relevant_msg=message,
                            )
                            actions_log.append(
                                f"Scanned a {msg_link} by {message.author.display_name} ({message.author.mention})"
                                f"and the word {flagged_word} flagged from the {check_name} check.\n"
                                f"Message content:\n{message.content}"
                            )
                            continue
                        actions_log.append(
                            f"Scanned a {msg_link} by {message.author.display_name} ({message.author.mention})"
                            f"and the word {flagged_word} flagged from the {check_name} check.\n"
                            f"Message content:\n{message.content}"
                        )

                if actions_log:
                    bytes = io.BytesIO("\n".join(actions_log).encode('utf-8'))
                    file = hikari.Bytes(bytes, "actions.txt")

                    embed = (
                        hikari.Embed(
                            title="Retroactive scan complete",
                            description=f"{len(actions_log)} Actions were taken against the detected messages{" and users" if viewself.penalize else ""}"
                        )
                    )

                    await ctx.edit_response(embed, attachment=file)
                else:
                    embed = (
                        hikari.Embed(
                            title="Retroactive scan complete",
                            description="There were no found messages that violated the content moderation rules."
                        )
                    )

                    await ctx.edit_response(embed, attachment=file)

        return Menu_Init()