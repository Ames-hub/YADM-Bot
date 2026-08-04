from modules.automod.commands.views.violation_show_img import views
from modules.automod.commands.group import group
from library.database.guilds import violations
from library.permissions import prechecks
from library.botapp import miru_client
from library import mainydb
import lightbulb
import hikari

loader = lightbulb.Loader()

@group.register
class command(
    lightbulb.SlashCommand,
    name="violation",
    description="View an individual case/violation ID record from the internal bot audit logs to see the specifics."
):

    entry_id = lightbulb.integer("case_id", "The ID of the infraction that was recorded.", min_value=1)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("automod-violations", ctx, hikari.Permissions.VIEW_AUDIT_LOG)

        item = violations.get_violation_record(self.entry_id)

        not_found_embed = hikari.Embed(
            title="Not found",
            description="This violation has not been logged, please check the ID and try again."
        )
        if item is None:
            await ctx.respond(not_found_embed)
            return
        if item.guild_id != ctx.guild_id:
            await ctx.respond(not_found_embed)
            return
        del not_found_embed

        whistleblower_txt = f"\n\nRecorded whistleblower: {item.whistleblower}" if item.whistleblower else ""
        embed = (
            hikari.Embed(
                title=f"Violation Record #{self.entry_id}",
                description=(
                    f"On {item.time.strftime("%d-%m-%Y")} at {item.time.strftime("%I:%M %P")}, {'an automated' if item.automated else 'a manual'} "
                    f"moderation decision was made by <@{item.reporter_id}> against <@{item.offender_id}>"
                    f"{whistleblower_txt}"
                )
            )
            .add_field(
                name="Offense",
                value=item.violation
            )
        )

        if item.extra_info:
            embed.add_field(
                name="Extra Data",
                value=item.extra_info
            )

        file = None
        if item.whistleblower == "Image Filter":
            img_bytes = mainydb.get_img(self.entry_id)
            if img_bytes:
                file = hikari.Bytes(img_bytes, "flagged_img.png", spoiler=True)

                view = views(ctx.guild_id, mod_id=ctx.user.id, embed=embed, photo=file)
                view_menu = view.init_view()
                resp = await ctx.respond(embed, components=view_menu.build())
                view.resp = resp

                miru_client.start_view(view_menu)
                await view_menu.wait()
                return

        await ctx.respond(embed)