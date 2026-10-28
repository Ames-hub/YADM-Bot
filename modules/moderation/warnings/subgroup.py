from library.botapp import client
import lightbulb

loader = lightbulb.Loader()
warnings_group = lightbulb.Group("warnings", "All the commands for managing warnings")

client.register(warnings_group)