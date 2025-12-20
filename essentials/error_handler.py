import lightbulb

loader = lightbulb.Loader()

@loader.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    # Basic error handler.
    # TODO: Upgrade the error handler to handle each different type of error.
    await exc.context.respond("An error occurred while executing the command.")
    return True