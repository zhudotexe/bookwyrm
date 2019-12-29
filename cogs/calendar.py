import asyncio
import re

import discord
from dateparser.search import search_dates
from discord.ext import commands

from models.games import Game
from utils import constants


class Calendar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #     bot.loop.create_task(self.test_on_history())
    #
    # async def test_on_history(self):
    #     await self.bot.wait_until_ready()
    #     chan = self.bot.get_channel(constants.DM_QUEST_CHANNEL)
    #     async for msg in chan.history():
    #         print(await self.parse_title(msg))
    #         await self.parse_time(msg)

    # ==== listeners ====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id not in (constants.DM_QUEST_CHANNEL, constants.PLAYER_QUEST_CHANNEL):
            return
        elif message.author.bot:  # ignore bot posts
            return
        elif '\n' not in message.content:  # ignore 1-line messages
            return
        elif re.match(r'^(<@&?\d+>\s*)+$', message.content):  # ignore ping-only messages
            return

        try:
            await self.handle_post(message)
        except CalendarException as e:
            await message.author.send(f"An error occurred parsing your game post:\n{e}\n"
                                      f"The post will not be tracked automatically.")
        except BadBotException:  # oh, ok
            return

    # ==== actors ====
    async def handle_post(self, message: discord.Message):
        title = await self.parse_title(message)
        time = await self.parse_time(message)

        game = Game.new(message, title, time)

    # ==== helpers ====
    async def parse_title(self, message: discord.Message):
        content = message.content
        if re.match(r'```\w*\n', content):  # first line is the opening of a code block
            first_line = content.splitlines()[1]
        else:
            first_line = content.splitlines()[0]

        # does it have the quest name in brackets on the first line?
        match = re.search(r'\[\s*(.+)\s*\]', first_line)
        if match:
            return match.group(1).strip()
        # return first_line.strip()  # todo

        # so what is the title?
        waiting_message = await message.channel.send(
            f"{message.author.mention} - I couldn't find the title of that quest posting. "
            f"What's the title? (Send it as a message here, or send `bad bot` if this isn't a quest posting.)"
        )
        try:
            reply = await self.bot.wait_for('message', check=reply_check_for(message), timeout=600)
        except asyncio.TimeoutError:
            raise CalendarException("Timed out waiting for the game title.")
        finally:
            await waiting_message.delete()

        await reply.delete()
        if reply.content.lower() == 'bad bot':
            raise BadBotException

        return reply.content.strip(' []')

    async def parse_time(self, message: discord.Message):
        possible_dates = search_dates(message.content, languages=['en'])
        print(possible_dates)


def reply_check_for(message):
    return lambda m: m.author.id == message.author.id and m.channel.id == message.channel.id


class CalendarException(Exception):
    pass


class BadBotException(Exception):
    """This exception causes Bookwyrm to feel sadness."""
    pass


def setup(bot):
    bot.add_cog(Calendar(bot))
