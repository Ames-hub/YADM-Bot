from library.database.auditing import server_logs
from modules.automod.commands.group import group
from library.permissions import perms
from library import datastore as ds
from datetime import datetime
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="exempt",
    description="Exempt someone from being flagged by the text filters for a bit!"
):
    
    user = lightbulb.user("target", "Who do you want to exempt?")

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)

        # Setup the dict and list if its not existing for this guild
        guild_id = int(ctx.guild_id)
        if ds.d["filter_exemptions"].get(guild_id, None) is None:
            ds.d["filter_exemptions"][guild_id] = []
        
        if self.user.id in ds.d["filter_exemptions"][guild_id]:
            await ctx.respond(
                hikari.Embed(
                    title="Already Exempted",
                    description="This user is already currently being exempted from the text automod.",
                    colour=0xff0000
                )
            )
            return

        ds.d["filter_exemptions"][guild_id].append(self.user.id)

        await ctx.respond(
            hikari.Embed(
                title="User Exempted",
                description="This user will not be blocked by the text moderation system.",
                colour=0xff0000
            )
        )
        
        logs = server_logs(guild_id)
        today = datetime.now().strftime("%d-%b-%Y")
        await logs.create_entry(
            hikari.Embed(
                title=f"User exempted from Automod",
                description=f"On {today}, Admin {ctx.user.mention} exempted {self.user.mention} from the text-based automod checks.",
                colour=0xff0000
            )
            .set_footer("To remove the exemption, run `/automod text unexempt`")
        )