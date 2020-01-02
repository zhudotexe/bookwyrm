import os
import sys

import motor.motor_asyncio
from discord.ext import commands

from models.rewards import SubmissionException
from utils import db

PREFIX = "."
TOKEN = os.getenv("TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB", "bookwyrm")
COGS = ("cogs.rewards", "cogs.onboarding", "cogs.calendar")


class Bookwyrm(commands.Bot):
    def __init__(self, *args, **kwargs):
        super(Bookwyrm, self).__init__(*args, **kwargs)
        self.mclient = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        self.mdb = self.mclient[MONGO_DB]


bot = Bookwyrm(PREFIX)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Error: {str(error)}")


@bot.event
async def on_error(*_, **__):
    _, error, _ = sys.exc_info()
    if isinstance(error, SubmissionException):
        return
    raise


@bot.event
async def on_message(message):
    await bot.process_commands(message)


for cog in COGS:
    bot.load_extension(cog)

if __name__ == '__main__':
    db.ensure_collections(bot.mdb)
    bot.run(TOKEN)
