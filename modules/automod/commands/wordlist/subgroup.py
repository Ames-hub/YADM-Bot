from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
wordlist_subgroup = automod_group.subgroup("wordlist", "All commands to modify the server' custom word list")