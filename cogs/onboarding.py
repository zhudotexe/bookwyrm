import discord
from discord.ext import commands

from utils import constants


class Onboarding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==== listeners ====
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.channel.id == constants.ROLLING_CHANNEL:
            return
        elif message.content.startswith("!randchar"):
            await self.ensure_player_role(message)

    # ==== actors ====
    @staticmethod
    async def ensure_player_role(message):
        # todo use id
        player_roles = [discord.utils.get(message.guild.roles, name=r) for r in constants.ROLES_TO_ASSIGN]
        filtered_roles = [r for r in player_roles if r and r not in message.author.roles]
        if filtered_roles:
            await message.author.add_roles(filtered_roles)
            # await message.author.send(constants.ONBOARDING_MESSAGE)


def setup(bot):
    bot.add_cog(Onboarding(bot))
