from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
muting_subgroup = automod_group.subgroup("mute", "All commands relating to muting")