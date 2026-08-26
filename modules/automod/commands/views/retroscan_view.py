from datetime import datetime, timezone, timedelta
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from datetime import datetime, timedelta
from library.botapp import botapp
from library.settings import get
from library import automod
import hikari
import miru
import io

PRIM_MAINTAINER = get.primary_maintainer()

async def do_retro_scan(
        guild_id:int,
        channel_id:int,
        mod_id:int,
        do_penalize:bool,
        do_kick:bool=None,
        do_ban:bool=None,
        lookback_hours:int=335
    ):
    # We cannot delete msgs older than two weeks, so if they're older than that, do not delete.
    do_delete = True
    if lookback_hours > 335:
        do_delete = False

    guild = dbguild(guild_id)
    if do_kick is None:
        do_kick = guild.get.text.do_kick_member()
    if do_ban is None:
        do_ban = guild.get.text.do_ban_member()
    if lookback_hours <= 335:
        do_delete = guild.get.text.do_delete_msg()  # IF they can be deleted, get if the guild wants them deleted.
    del guild

    # Get all messages within the time frame.
    target_timestamp = int(datetime.now(timezone.utc).timestamp() - timedelta(hours=lookback_hours).total_seconds())
    target_time = datetime.fromtimestamp(target_timestamp)
    try:
        fetched_messages = await botapp.rest.fetch_messages(channel_id, after=target_time)
    except (hikari.ForbiddenError, hikari.UnauthorizedError):
        return False

    log_msg = f"<#{channel_id}> Is currently undergoing a retro-scan as ordered by <@{mod_id}>, scanning onwards from <t:{target_timestamp}:f> to now."
    if do_penalize:
        log_msg += f"\nPenalties are being applied, users will be"
        log_msg += f"{" banned," if do_ban else ""}{" and" if do_ban and do_kick else ""}{" kicked" if do_kick else ""}"

    await server_logs(guild_id).create_entry(
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
        bad_msg, check_name, flagged_word, _ = automod.text_check(message.content, message.guild_id)
        if bad_msg:
            msg_link = f"message (link: {message.make_link(message.guild_id)})"
            if do_penalize:
                if do_kick or do_ban:
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
                await dbguild(message.guild_id).handle_like_guilty(
                    user_id=message.author.id,
                    reason=reason,
                    mod_id=mod_id,
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

    return actions_log

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
        if self.hours_back >= 335:
            embed.add_field(
                name="Discord Limits",
                value="Bots cannot delete messages older than two weeks, if you proceed, messages older than two weeks will not be deleted."
            )
        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Cancel", style=hikari.ButtonStyle.SUCCESS)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if not ctx.author.id == viewself.mod_id:  # Prevents others from clicking it
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
            async def do_scan(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if not ctx.author.id == viewself.mod_id:  # Prevents others from clicking it
                    return

                await ctx.respond(
                    hikari.Embed(
                        title="Scanning...",
                        description="This may take a while, please hold tight for a couple minutes!",
                        colour=0xFFA500
                    )
                )

                try:
                    actions_log = await do_retro_scan(
                        guild_id=ctx.guild_id,
                        channel_id=viewself.channel,
                        mod_id=viewself.mod_id,
                        do_penalize=viewself.penalize,
                        do_kick=viewself.do_kick,
                        do_ban=viewself.do_ban,
                        lookback_hours=viewself.hours_back
                    )
                except hikari.ForbiddenError:
                    await ctx.edit_response(
                        hikari.Embed(
                            title="Bad Bot Permissions",
                            description="We do not have permission to fetch messages that far back.",
                            colour=0xff0000
                        )
                    )
                    return

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

            if viewself.mod_id == PRIM_MAINTAINER:
                @miru.button(
                    label="Observation Scan",
                    style=hikari.ButtonStyle.SECONDARY,
                    emoji="🔎"
                )
                async def do_observe_scan(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if not ctx.author.id == viewself.mod_id:  # Prevents others from clicking it
                        return

                    raise NotImplementedError
                    # TODO: Implement this

        return Menu_Init()