from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("activity", "All the commands for user leveling.")

client.register(group)