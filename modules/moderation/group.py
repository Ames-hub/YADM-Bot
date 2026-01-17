from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("moderation", "All the commands for server moderation.")

client.register(group)