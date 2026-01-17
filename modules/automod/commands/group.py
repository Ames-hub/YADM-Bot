from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("automod", "All the commands for control of our automod.")

client.register(group)