from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("reactionroles", "All the commands for reaction roles.")

client.register(group)