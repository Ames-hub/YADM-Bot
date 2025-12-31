"""
This is a library meant to replace hikari-lightbulb's bot.d that has been removed in this "new" and "improved" version 3
And was replaced with dependency injections, a much more complicated, and quite frankly, over-kill piece of bloatware.

The reason this exists is as follows:
1. This is global, accessible in all parts of the project opposed to JUST commands.
2. It is mutable, so it can be updated whenever.
3. Its just fuckin' simple. No over-engineered insanity.

Additionally, as a part of python, when a module is imported, it only executes the file ONCE.
Meaning when app.py runs this file, it'll create the datastore dict and it'll then preserve that dictionary forever after (until process end or crash)
"""

d = {}