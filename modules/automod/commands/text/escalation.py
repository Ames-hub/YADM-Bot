from modules.automod.commands.views.escalation_view import views
from modules.automod.commands.text.subgroup import text_subgroup
from library.database.guilds import dbguild
from library.permissions import prechecks
from library.botapp import miru_client
from lightbulb import Choice
import lightbulb
import hikari

loader = lightbulb.Loader()

choices_options = [
    Choice("One Warning", "1"),
    Choice("Two Warnings", "2"),
    Choice("Three Warning", "3"),
    Choice("Four Warnings", "4")
]

@text_subgroup.register
class command(
    lightbulb.SlashCommand,
    name="escalation",
    description="Set how we should escalate based on multiple similar rule violations.",
):
    
    del_msg_thres = lightbulb.string("delete-msg", "How many warnings until we start deleting their message?", choices=choices_options, default=None)
    cooldown_thres = lightbulb.string("cooldown", "How many warnings to give a very short mute? or \"cooldown?\"", choices=choices_options, default=None)
    mute_thres = lightbulb.string("mute-member", "How many warnings until they get a full, temporary mute?", choices=choices_options, default=None)
    kick_thres = lightbulb.string("kick-member", "How many warnings until we kick them?", choices=choices_options, default=None)
    ban_thres = lightbulb.string("ban-member", "How many warnings until we ban them?", choices=choices_options, default=None)

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        await prechecks("text-am-escalation", ctx, hikari.Permissions.ADMINISTRATOR)

        if not self.del_msg_thres and not self.cooldown_thres and not self.mute_thres and not self.kick_thres and not self.ban_thres:
            view = views(ctx.guild_id, ctx.user.id)
            embed = view.gen_embed()
            view_menu = view.init_view()

            resp = await ctx.respond(
                embed=embed,
                components=view_menu.build(),
                flags=hikari.MessageFlag.EPHEMERAL
            )
            view.ctx = ctx
            view.resp = resp

            miru_client.start_view(view_menu)
            await view_menu.wait()
        else:
            guild = dbguild(ctx.guild_id)
            string = ""
            if self.del_msg_thres:
                success = guild.set.text.escalation.msg_deletion(int(self.del_msg_thres))
                if success:
                    string += f"- Message deletion now occurs at {self.del_msg_thres} warnings.\n"
                else:
                    string += "- Failed to set message deletion threshold.\n"
            if self.cooldown_thres:
                success = guild.set.text.escalation.cooldown_threshold(int(self.cooldown_thres))
                if success:
                    string += f"- User cooldowns now occurs at {self.cooldown_thres} warnings.\n"
                else:
                    string += "- Failed to set user cooldown threshold.\n"
            if self.mute_thres:
                success = guild.set.text.escalation.mute_threshold(int(self.mute_thres))
                if success:
                    string += f"- User muting now occurs at {self.mute_thres} warnings.\n"
                else:
                    string += "- Failed to set user muting threshold.\n"
            if self.kick_thres:
                success = guild.set.text.escalation.kick_member(int(self.kick_thres))
                if success:
                    string += f"- User muting now occurs at {self.kick_thres} warnings.\n"
                else:
                    string += "- Failed to set user kicking threshold.\n"
            if self.ban_thres:
                success = guild.set.text.escalation.ban_member(int(self.ban_thres))
                if success:
                    string += f"- User banning now occurs at {self.ban_thres} warnings.\n"
                else:
                    string += "- Failed to set user banning threshold.\n"

            embed = (
                hikari.Embed(
                    title="Escalation Settings",
                    description="Escalation settings have been changed as below."
                )
            )
            if string:
                embed.add_field(value=string)
            else:
                embed.add_field(value="No actions were performed?")
            await ctx.respond(embed)