from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("leveling", "All the commands for user leveling.")

client.register(group)