from library.database.observations import generate_automod_report
from library.settings import observe_conf, get
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.message.content == "--give-report":
        return
    if not observe_conf.get_enabled():
        return
    if not get.primary_maintainer() == event.author.id:
        return

    pdf_bytes = generate_automod_report()
    file = hikari.Bytes(pdf_bytes, "report.pdf")

    embed = (
        hikari.Embed(
            title="Automod QA Report Summary",
            description="We've compiled a report showing exactly where the bot's automod quality is at.",
            colour=0x0000ff
        )
    )

    await event.message.respond(embed, attachment=file)