from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
honeypot_subgroup = automod_group.subgroup("honeypot", "All commands relating to the honeypot")