from library.database.auditing import server_logs
from modules.automod.commands.group import group
from library.permissions import prechecks
from library import datastore as ds
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="unexempt",
    description="Removes the exemption from being flagged by the text filters."
):
    
    user = lightbulb.user("target", "Who do you want to unexempt?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("unexempt-user", ctx, hikari.Permissions.ADMINISTRATOR)

        # Setup the dict and list if its not existing for this guild
        guild_id = int(ctx.guild_id)
        if ds.d["filter_exemptions"].get(guild_id, None) is None:
            ds.d["filter_exemptions"][guild_id] = []
        
        if self.user.id not in ds.d["filter_exemptions"][guild_id]:
            await ctx.respond(
                hikari.Embed(
                    title="Not Exempted",
                    description="This user is not being exempted currently.",
                    colour=0xff0000
                )
            )
            return
        
        ds.d["filter_exemptions"][guild_id].remove(self.user.id)

        await ctx.respond(
            hikari.Embed(
                title="Exemption Removed",
                description="This user will now be treated normally by the text moderation system.",
                colour=0x00ff00
            )
        )
        
        logs = server_logs(guild_id)
        today = datetime.now().strftime("%d-%b-%Y")
        await logs.create_entry(
            hikari.Embed(
                title=f"Automod Exemption Removed",
                description=f"On {today}, Admin {ctx.user.mention} removed the exemption for {self.user.mention} from the text-based automod checks.",
                colour=0x00ff00
            )
        )