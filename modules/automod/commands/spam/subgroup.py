from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
spam_subgroup = automod_group.subgroup("spam", "All commands relating to spam automoderation")