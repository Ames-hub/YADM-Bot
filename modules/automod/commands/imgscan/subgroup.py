from modules.automod.commands.group import group as automod_group
import lightbulb

loader = lightbulb.Loader()
imgscan_subgroup = automod_group.subgroup("image", "All commands relating to the image scanner")