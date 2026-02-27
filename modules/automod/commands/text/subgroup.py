from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
text_subgroup = automod_group.subgroup("text", "All commands relating to text automoderation")