from library.botapp import botapp
from library.settings import get
import lightbulb
import hikari

loader = lightbulb.Loader()

async def handle_botjoin_event(channel:int):
    if not channel:
        return
    
    embed = (
        hikari.Embed(
            title=f"{get.bot_name()} Has Joined!",
            description="Hello! Thank you for picking me. This is a basic summary of how to get started with me!",
            colour=0xff00ff
        )
        .add_field(
            name="Purpose",
            value="I am primarily a moderation bot, though I can also do much more quite well as well!"
        )
        .add_field(
            name="Getting Started",
            value="""
To get started, I'd recommend you do the following.

Simple:
1. Run `/setup` (and nothing more, you're done from there. Bot will handle it.)

If your server has recently been hit by a hate-raid, or there's otherwise swarms of bad messages, run `/automod retroscan`
after running `/setup` or doing the complex setup.
"""
        )
        .add_field(
            name="Complex Setup",
            value="""
1. If you have any words you do not want said, add them to the bad word list! use `/automod wordlist add`
2. Decide if you want to use only your own custom word list, or if you want to use the default one as well! Use `/automod text presetlist` to configure this.
3. Use the command `/automod modules`! This'll let you configure what we look for!

If you want to use text moderaton, see `/automod text settings`, this'll let you configure penalties for text rule violations.
If you want to block NSFW Images, see `/automod imgscan penalties`
If you want to block spam, see `/automod spam penalties`
"""
        )
    )

    try:
        await botapp.rest.create_message(
            channel=channel,
            embed=embed
        )
    except (hikari.UnauthorizedError, hikari.ForbiddenError, hikari.NotFoundError):
        pass

@botapp.listen(hikari.events.GuildJoinEvent)
async def listener(event: hikari.events.GuildJoinEvent):
    channel = event.guild.system_channel_id
    if not channel:
        channel = await botapp.rest.fetch_guild(event.guild_id)
        channel = channel.system_channel_id
    return await handle_botjoin_event(channel)