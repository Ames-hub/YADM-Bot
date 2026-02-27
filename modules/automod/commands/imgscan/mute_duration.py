from modules.automod.commands.imgscan.subgroup import imgscan_subgroup
from library.database.auditing import server_logs
from library.database.guilds import dbguild
from library.permissions import perms
import lightbulb
import hikari

loader = lightbulb.Loader()

@imgscan_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="mutelength",
    description="Set the default length for how long an image-violation mute is."
):
    
    minutes = lightbulb.integer("minutes", "How many minutes must pass before the mute is undone", min_value=1, max_value=9007199254740991)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await perms.perms_precheck(hikari.Permissions.ADMINISTRATOR, ctx)
        
        seconds_duration = self.minutes * 60
        guild = dbguild(ctx.guild_id)
        success = guild.set.images.set_mute_duration(seconds_duration)

        if success:
            embed = hikari.Embed(
                title="Mute Duration Set",
                description=f"When a user violates image content rules, they will be muted for {self.minutes} minutes.",
                color=0x00ff00
            )
            await ctx.respond(embed)
            await server_logs(ctx.guild_id).create_entry(embed=embed)
        else:
            embed = hikari.Embed(
                title="Mute Duration Not Set",
                description=f"We couldn't set the image mute duration for some reason!"
            )
            await ctx.respond(embed)