from modules.moderation.warnings.subgroup import warnings_group
from library.database.guilds import dbguild
from library.permissions import prechecks
from library import datastore as ds
import lightbulb
import hikari

loader = lightbulb.Loader()

@warnings_group.register
class command(
    lightbulb.SlashCommand,
    name="get",
    description="Get a specific warning by its ID"
):
    
    warn_id = lightbulb.integer("warn_id", "The ID of the warning to fetch", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("get warning", ctx, hikari.Permissions.MANAGE_MESSAGES)

        guild = dbguild(ctx.guild_id)
        warn = guild.warnings.get_by_id(self.warn_id)
        if not warn:
            await ctx.respond(
                hikari.Embed(
                    title="Non-existant warning",
                    description="No warns under this ID Exist.",
                    colour=0xffff00
                )
            )
            return

        embed = (
            hikari.Embed(
                title=f"Warning #{warn.warn_id} - {warn.time.strftime("%d-%m-%Y")}",
                description=(
                    f"<@{warn.user_id}> was warned for the following reason:\n\"{warn.reason}\""
                ),
                colour=0xff0000
            )
            .add_field(
                name="Moderator Details",
                value=(
                    "This warn was automated and created by me"
                    if ds.d['myid'] == warn.moderator_id else
                    f"This warn was issued by <@{warn.moderator_id}>"
                )
            )
        )

        await ctx.respond(embed)