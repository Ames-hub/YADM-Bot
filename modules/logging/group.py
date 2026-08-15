from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("logging", "All the commands for server logging.")

client.register(group)