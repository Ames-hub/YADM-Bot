from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
group = lightbulb.Group("joinroles", "All the commands for roles given to new members.")

client.register(group)