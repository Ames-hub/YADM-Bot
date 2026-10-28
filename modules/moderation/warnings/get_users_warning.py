from modules.moderation.warnings.subgroup import warnings_group
from library.database.guilds import dbguild
from library.permissions import prechecks
from library import datastore as ds
from math import ceil
import lightbulb
import hikari

loader = lightbulb.Loader()

@warnings_group.register
class command(
    lightbulb.SlashCommand,
    name="getall",
    description="Get all warnings for a specific user."
):
    
    target = lightbulb.user("target", "The user you're wanting fetch warnings for")
    # Index from 1
    page = lightbulb.integer("page", "If there's more than one page, view which one to view", default=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("get user warnings", ctx, hikari.Permissions.MANAGE_MESSAGES)

        guild = dbguild(ctx.guild_id)
        warn_list = guild.warnings.get_by_user(self.target.id)

        if len(warn_list) == 0:
            await ctx.respond(
                hikari.Embed(
                    title="No warnings",
                    description="This user has received no warnings since they first joined.",
                    colour=0xffff00
                )
            )
            return

        # Calculate pagination
        warnings_per_page = 10
        total_pages = max(1, ceil(len(warn_list) / warnings_per_page))
        page = self.page or 1

        # Validate the requested page
        if page < 1 or page > total_pages:
            await ctx.respond(
                hikari.Embed(
                    title="Invalid page",
                    description=f"Please choose a page between 1 and {total_pages}."
                )
            )
            return

        # Get only the warnings for this page
        start = (page - 1) * warnings_per_page
        end = start + warnings_per_page
        page_warnings = warn_list[start:end]

        embed = hikari.Embed(
            title=f"{len(warn_list)}x User Warnings",
            description=f"Page {page}/{total_pages} | Showing {len(page_warnings)} warnings",
            colour=0xff0000
        )

        for warn in page_warnings:
            embed.add_field(
                name=f"Warning #{warn.warn_id} - {warn.time.strftime('%d-%m-%Y')}",
                value=(
                    f"<@{warn.user_id}> was warned for the following reason:\n"
                    f"\"{warn.reason}\"\n\n"
                    "This warn was automated and created by me."
                    if ds.d['myid'] == warn.moderator_id else
                    f"This warn was issued by <@{warn.moderator_id}>"
                )
            )

        await ctx.respond(embed)
