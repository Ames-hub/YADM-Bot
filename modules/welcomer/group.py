from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("welcomer", "All the commands for server welcoming module.")

client.register(group)