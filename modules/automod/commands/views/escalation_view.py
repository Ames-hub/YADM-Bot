from library.database.auditing import server_logs
from library.database.guilds import dbguild
import hikari
import miru

strike_1_style = hikari.ButtonStyle.DANGER
strike_2_style = hikari.ButtonStyle.PRIMARY
strike_3_style = hikari.ButtonStyle.SUCCESS
strike_4_style = hikari.ButtonStyle.SECONDARY

def cycle(number:int):
    """ Automatically cycles the level to the next one """
    if number == 1:
        return 2
    elif number == 2:
        return 3
    elif number == 3:
        return 4
    elif number == 4:
        return 1
    else:
        return 1
    
def get_cycle_style(number:int):
    if number == 1:
        return strike_1_style
    elif number == 2:
        return strike_2_style
    elif number == 3:
        return strike_3_style
    elif number == 4:
        return strike_4_style
    else:
        return strike_1_style

class views:
    def __init__(self, guild_id, mod_id):
        self.guild_id = guild_id
        self.guild = dbguild(self.guild_id)
        self.mod_id = mod_id
        self.current_escalation = self.guild.get.text.escalation._get_record()

        self.do_del_msg = self.guild.get.text.do_delete_msg()
        self.do_cooldown = self.guild.get.text.do_cooldown()
        self.do_mute_member = self.guild.get.text.do_mute_member()
        self.do_kick_member = self.guild.get.text.do_kick_member()
        self.do_ban_member = self.guild.get.text.do_ban_member()
        self.escalation_window = self.guild.get.escalation_window()
        self.do_escalate = self.guild.get.do_escalate()

    def gen_embed(self):
        embed = (
            hikari.Embed(
                title="Automod Text Filter | Escalation",
                description=(
                    "Use the buttons below to control how we escalate punishment according to how many times a user is warned.\n\n"
                    "*To punish on one strike, cycle the button to Red.*\n"
                    "*To punish on two strikes, cycle the button to Blue.*\n"
                    "*To punish on three strikes, cycle the button to Green.*\n"
                    "*To punish on four strikes, cycle the button to Dark-Grey.*\n\n"
                    "To disable one of these penalties entirely, use `/automod text penalties` to turn one off!\n\n"
                    "-# (The escalation window describes how long it takes for a warning to be forgiven)\n"
                    f"**Current Escalation window: {self.escalation_window // 3600 } Hours**"
                ),
                colour=0x00ffff
            )
        )
        if not self.do_del_msg and not self.do_cooldown and not self.do_mute_member and not self.do_kick_member and not self.do_ban_member:
            embed.add_field(
                name="No active punishments",
                value=(
                    "All active punishments have been turned off by the server settings. "
                    "Please review `/automod text penalties` and see which you'd like to use"
                )
            )
        if not self.guild.get.text.do_warn_member():
            embed.add_field(
                name="Warnings disabled ⚠️",
                value=(
                    "Warnings are not an active penalty on this server,"
                    " and escalation will not work until you turn it on. Click the button below to enable it."
                )
            )
        if not self.guild.get.do_escalate():
            embed.add_field(
                name="Module disabled ⚠️",
                value=(
                    "Escalation has been disabled."
                    " Escalation will not work until you turn it on. Click the button below to toggle it on."
                )
            )

        return embed

    def init_view(viewself):
        class Menu_Init(miru.View):
            @miru.button(label="Save", emoji="💾", style=hikari.ButtonStyle.SECONDARY, row=1)
            async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.author.id != viewself.mod_id:
                    return
                await ctx.edit_response(
                    hikari.Embed(
                        title="Exiting menu.",
                        description="Your settings have been saved.",
                    ),
                    components=[]
                )
                self.stop()

            async def on_timeout(self) -> None:
                await viewself.ctx.edit_response(
                    viewself.resp,
                    embed=hikari.Embed(
                        title="Menu Exitted",
                        description="This menu has closed itself after being left open for too long."
                    ),
                    components=[]
                )

            if viewself.do_del_msg:
                @miru.button(
                    label=f"{viewself.current_escalation.del_msg_threshold}) Delete Message",
                    style=get_cycle_style(viewself.current_escalation.del_msg_threshold),
                    row=0
                )
                async def escalate_delmsg_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    cycle_no = cycle(viewself.current_escalation.del_msg_threshold)
                    viewself.guild.set.text.escalation.msg_deletion(cycle_no)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    button.label = f"{cycle_no}) Delete Message"
                    button.style = get_cycle_style(cycle_no)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Escalation Settings Changed",
                            description=f"After {cycle_no} warnings, offending messages will be deleted."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

            if viewself.do_cooldown:
                @miru.button(
                    label=f"{viewself.current_escalation.cooldown_threshold}) Cooldown Member",
                    style=get_cycle_style(viewself.current_escalation.cooldown_threshold),
                    row=0
                )
                async def escalate_cooldown_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    cycle_no = cycle(viewself.current_escalation.cooldown_threshold)
                    viewself.guild.set.text.escalation.cooldown_threshold(cycle_no)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    button.label = f"{cycle_no}) Cooldown Member"
                    button.style = get_cycle_style(cycle_no)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Escalation Settings Changed",
                            description=f"After {cycle_no} warnings, we will place the user on a cooldown."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

            if viewself.do_mute_member:
                @miru.button(
                    label=f"{viewself.current_escalation.mute_threshold}) Mute Member",
                    style=get_cycle_style(viewself.current_escalation.mute_threshold),
                    row=0
                )
                async def escalate_mute_member_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    cycle_no = cycle(viewself.current_escalation.mute_threshold)
                    viewself.guild.set.text.escalation.mute_threshold(cycle_no)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    button.label = f"{cycle_no}) Mute Member"
                    button.style = get_cycle_style(cycle_no)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Escalation Settings Changed",
                            description=f"After {cycle_no} warnings, users will be muted for violations."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

            if viewself.do_kick_member:
                @miru.button(
                    label=f"{viewself.current_escalation.kick_member_threshold}) Kick Member",
                    style=get_cycle_style(viewself.current_escalation.kick_member_threshold),
                    row=0
                )
                async def escalate_kick_member_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    cycle_no = cycle(viewself.current_escalation.kick_member_threshold)
                    viewself.guild.set.text.escalation.kick_member(cycle_no)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    button.label = f"{cycle_no}) Kick Member"
                    button.style = get_cycle_style(cycle_no)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Escalation Settings Changed",
                            description=f"After {cycle_no} warnings, we will kick the user from the server."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

            if viewself.do_ban_member:
                @miru.button(
                    label=f"{viewself.current_escalation.ban_member_threshold}) Ban Member",
                    style=get_cycle_style(viewself.current_escalation.ban_member_threshold),
                    row=0
                )
                async def escalate_ban_member_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    cycle_no = cycle(viewself.current_escalation.ban_member_threshold)
                    viewself.guild.set.text.escalation.ban_member(cycle_no)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    button.label = f"{cycle_no}) Ban Member"
                    button.style = get_cycle_style(cycle_no)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Escalation Settings Changed",
                            description=f"After {cycle_no} warnings, we will ban the user from the server."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

            @miru.button(
                label="Toggle Escalation",
                style=hikari.ButtonStyle.PRIMARY if viewself.guild.get.do_escalate() else hikari.ButtonStyle.SECONDARY,
                row=1,
            )
            async def toggle_escalation_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                if ctx.author.id != viewself.mod_id:
                    return
                viewself.guild.set.do_escalate(not viewself.do_escalate)
                viewself.do_escalate = not viewself.do_escalate
                viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                button.style = hikari.ButtonStyle.PRIMARY if viewself.do_escalate else hikari.ButtonStyle.SECONDARY
                await ctx.edit_response(viewself.gen_embed(), components=self)
                await server_logs(ctx.guild_id).create_entry(
                    hikari.Embed(
                        title="Escalation Toggled",
                        description=f"Escalation has been {"turned off." if not viewself.do_escalate else "enabled."}"
                    )
                    .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                )

            if not viewself.guild.get.text.do_warn_member():
                @miru.button(
                    label="Enable Warnings Now?",
                    emoji="⚠️",
                    style=hikari.ButtonStyle.DANGER,
                    row=0,
                    custom_id="warnings-enable-btn"
                )
                async def enable_warnings_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
                    if ctx.author.id != viewself.mod_id:
                        return
                    viewself.guild.set.text.do_warn_member(True)
                    viewself.current_escalation = viewself.guild.get.text.escalation._get_record()
                    self.remove_item(button)
                    await ctx.edit_response(viewself.gen_embed(), components=self)
                    await server_logs(ctx.guild_id).create_entry(
                        hikari.Embed(
                            title="Text filtering Setting Changed",
                            description=f"Warnings will now be issued to users on text filtering infractions."
                        )
                        .set_footer("'Escalation' is what we refer to as the system we use to punish users harsher and harsher based on recent warnings.")
                    )

        return Menu_Init(timeout=60)