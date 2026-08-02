from modules.automod.commands.text.subgroup import text_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import prechecks
import lightbulb
import hikari

loader = lightbulb.Loader()

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="ban_delete_time",
    description="When/if a user is banned, how far back should we delete their messages in the server?"
):
    
    minutes = lightbulb.integer("minutes", "How many minutes must pass before the mute is undone", min_value=1, max_value=1209600)  # 2 Weeks

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("text-setban-msg-purge-time", ctx, hikari.Permissions.ADMINISTRATOR)
        
        seconds_duration = self.minutes * 60
        guild = dbguild(ctx.guild_id)
        success = guild.set.text.set_ban_msg_purgetime(seconds_duration)

        if success:
            embed = hikari.Embed(
                title="Deletion Time Set",
                description=f"When a user violates text content rules, their messages younger than {self.minutes} minutes will be deleted.",
                color=0x00ff00
            )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(embed=embed)
        else:
            embed = hikari.Embed(
                title="Deletion Time Not Set",
                description=f"We couldn't set the on-ban message deletion duration for some reason!"
            )
            await ctx.respond(embed)