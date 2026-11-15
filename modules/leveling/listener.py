from library.database.leveling import user_activity
from library.database.guilds import dbguild
from library.botapp import botapp
import lightbulb
import hikari

loader = lightbulb.Loader()

@loader.listener(hikari.GuildMessageCreateEvent)
async def botfunction(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    guild = dbguild(event.guild_id)
    if not guild.leveling.get_enabled():
        return

    # You get more points for every 50 characters in the message
    # Gets how many times the text content len goes into 50, then multiplies by 5.
    # Always returns 5 at minimum.
    exp_earned = max((len(event.message.content) // 50) * 5, 5)

    result = guild.leveling.give_exp(
        user_id=event.author.id,
        exp=exp_earned,
        check_level=True
    )

    if result['lvl_is_diff']:

        old_lvl = result['old_lvl']
        new_lvl = result['new_lvl']
        ua = user_activity(event.guild_id)

        if new_lvl > old_lvl:
            embed = hikari.Embed(
                title="Level Up! ✨",
                description=f"Congratulations {event.author.mention},\nyou just leveled up to level {new_lvl}!",
                colour=0xFFD700
            )
            leveling_perk = guild.leveling.get_guild_level_perk(new_lvl)
            activity_perk = ua.get_role_perk(role_id=leveling_perk.role_id)

            # If its an activity perk and a leveling perk, behave differently.
            is_activity_perk = (
                activity_perk is not None
                and
                ua.get_guild_enabled() is True
            )
            msgs_count = ua.get_msgs_count(event.author.id) if is_activity_perk else None

            if leveling_perk is not None:
                give_perks = True
                if is_activity_perk and activity_perk.msgs_required >= msgs_count:
                    embed.add_field(
                        name="New Perks!",
                        value=f"You've unlocked the perks that come with the role <@&{leveling_perk.role_id}>"
                    )
                    give_perks = False
                elif is_activity_perk and not activity_perk.msgs_required >= msgs_count:
                    give_perks = False
                    msgs_needed = activity_perk.msgs_required - msgs_count
                    if msgs_needed > 999:
                        embed.add_field(
                            name="You'll get there eventually!",
                            value=f"You leveled up, but you're {msgs_needed} messages short of unlocking new perks!"
                        )
                    else:
                        embed.add_field(
                            name="Almost there!",
                            value=f"You leveled up, but you're {msgs_needed} messages short of unlocking new perks!"
                        )
                elif not activity_perk:
                    give_perks = True
                    embed.add_field(
                        name="New Perks!",
                        value=f"You've unlocked the perks that come with the role <@&{leveling_perk.role_id}>"
                    )

                if give_perks:
                    try:
                        await botapp.rest.add_role_to_member(
                            event.guild_id,
                            event.author.id,
                            leveling_perk.role_id,
                            reason="User leveled up!"
                        )
                    except (hikari.ForbiddenError, hikari.UnauthorizedError, hikari.BadRequestError, hikari.NotFoundError):
                        embed.add_field(
                            name="Error adding perk!",
                            value=f"We tried to add the perk role, but it seems we lack permission to do so, or the role does not exist anymore."
                        )
                        # Remove it so we don't spam discord with impossible requests.
                        guild.leveling.rm_level_role(leveling_perk.role_id)

            channel = guild.leveling.get_dedicated_channel()
            if channel is not None:
                await botapp.rest.create_message(
                    channel,
                    embed
                )
            else:
                await event.message.respond(embed)