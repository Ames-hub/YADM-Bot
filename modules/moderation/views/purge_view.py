from library.database.auditing import server_logs
from library.database.guilds import dbguild
import datetime
import hikari
import miru


class views:
    def __init__(self, guild_id, delete_after: datetime.datetime, channel:int, reason:str):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.delete_after: datetime.datetime = delete_after
        self.channel_id = channel
        self.reason = reason

    def gen_embed(self):
        date = self.delete_after.strftime('%Y-%b-%d %I:%M %p')
        embed = hikari.Embed(
            title="Purge Confirmation",
            description=f"Do you want to purge messages all messages after {date}? This action is irreversible!",
            colour=0xFFA500
        )
        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Cancel", style=hikari.ButtonStyle.SECONDARY)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await ctx.edit_response(
                    hikari.Embed(
                        title="Cancelled",
                        description="Purge has been cancelled.",
                    ),
                    components=[]
                )
                self.stop()

            @miru.button(
                label="Delete Messages",
                style=hikari.ButtonStyle.DANGER,
                emoji="🗑️"
            )
            async def delete(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                await ctx.edit_response(
                    hikari.Embed(
                        title="Purge Initiated",
                        description=(
                            f"Messages in <#{viewself.channel_id}> that were sent after {viewself.delete_after.strftime('%Y-%b-%d %I:%M %p')}\n"
                            "are being purged. This may take a moment depending on the number of messages."
                        ),
                        colour=0xFFA500
                    ),
                    flags=hikari.MessageFlag.EPHEMERAL,
                    components=[]
                )
                success = await viewself.guild.purge_messages(
                    moderator_id=ctx.user.id,
                    channel_id=viewself.channel_id,
                    after=viewself.delete_after,
                    reason=viewself.reason
                )
                if not success:
                    await ctx.edit_response(
                        hikari.Embed(
                            title="Purge Failed",
                            description="An error occurred while trying to purge messages. Please try again later.",
                            colour=0xFF0000
                        ),
                        components=[]
                    )
                self.stop()

        return Menu_Init()