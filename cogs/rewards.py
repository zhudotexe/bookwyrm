import asyncio
import datetime
import re

import discord
from discord.ext import commands, tasks
from natural import date

from models.rewards import Opinion, RewardSubmission, Vote
from utils import constants

VOTE_MAP = {
    "\U0001f44d": Opinion.UPVOTE,
    "\U0000270b": Opinion.COMMENT,
    "\U0001f44e": Opinion.DOWNVOTE
}


class Rewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notifier.start()

    # ==== listeners ====
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.channel.id == constants.REWARDS_CHANNEL:
            return
        await self.new_submission(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        await self.update_submission(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        await self.untrack_submission(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.add_vote(payload.message_id, payload.user_id, payload.emoji.name)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.remove_vote(payload.message_id, payload.user_id, payload.emoji.name)

    # ==== scheduled tasks ====
    # noinspection PyCallingNonCallable
    @tasks.loop(hours=24)
    async def notifier(self):
        await self.do_notification()

    @notifier.before_loop
    async def before_printer(self):
        """wait until next noon"""
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        next_time = datetime.datetime.now()
        if now.hour > constants.SCHEDULED_HOUR:
            next_time += datetime.timedelta(days=1)
        next_time = datetime.datetime(year=next_time.year, month=next_time.month, day=next_time.day,
                                      hour=constants.SCHEDULED_HOUR)
        seconds = (next_time - now).total_seconds()
        await asyncio.sleep(seconds)

    # ==== commands ====
    @commands.command()
    async def rewards(self, ctx):
        await self.do_notification(no_ping=True, destination=ctx)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def debug_untrack(self, ctx, message_id: int):
        submission = await RewardSubmission.from_id(self.bot.mdb, message_id)
        await submission.untrack(self.bot.mdb)
        await ctx.add_reaction("\U0001f44d")

    # ==== doing things ====
    # ---- new submission ----
    async def new_submission(self, message):
        # check against template
        lines = message.content.splitlines()
        if len(lines) < 2:
            return await self._bad_submission(message)
        title = lines[0].strip()
        levels = list(map(int, re.findall(r'\d+', lines[1])))

        if not (len(levels) and all(0 < lvl < 21 for lvl in levels)):
            return await self._bad_submission(message, reason=f"Invalid levels: {levels}")

        # create entry
        submission = RewardSubmission.new(title, message)
        await submission.commit(self.bot.mdb)

        await message.author.send(f"Okay! I'm now tracking a reward submission for {submission.quest_title}.")

    @staticmethod
    async def _bad_submission(message, reason=''):
        if reason:
            reason = f"{reason}\n"
        await message.author.send(f"I could not track your reward submission.\n{reason}"
                                  f"Please make sure to follow this template: ```\nQUEST TITLE\nLevels: X, Y, Z...\n\n"
                                  f"More info and submission details\n```Here's the message you posted:")
        await message.author.send(f"```\n{message.content}\n```")
        await message.delete()

    # ---- submission edited ----
    async def update_submission(self, message_id):
        submission = await RewardSubmission.from_id(self.bot.mdb, message_id)
        submission.time_last_edited = datetime.datetime.now()
        await submission.commit(self.bot.mdb)

        author = self.bot.get_user(submission.author)
        await author.send(f"I have tracked an update to {submission.quest_title}!")

    # ---- votes ----
    async def add_vote(self, message_id, author_id, emoji):
        submission = await RewardSubmission.from_id(self.bot.mdb, message_id)
        author = self.bot.get_user(author_id)
        if emoji not in VOTE_MAP:
            return await author.send(f"I'm not sure how to interpret {emoji}.")

        vote = Vote.new(author_id, VOTE_MAP[emoji])
        submission.votes.append(vote)

        await submission.commit(self.bot.mdb)
        await author.send(f"Tracked your vote on {submission.quest_title}!")

    async def remove_vote(self, message_id, author_id, emoji):
        submission = await RewardSubmission.from_id(self.bot.mdb, message_id)
        author = self.bot.get_user(author_id)
        if emoji not in VOTE_MAP:
            return
        opinion = VOTE_MAP[emoji]

        try:
            vote = next(v for v in submission.votes if v.author == author_id and v.opinion == opinion)
        except StopIteration:
            return

        submission.votes.remove(vote)

        await submission.commit(self.bot.mdb)
        await author.send(f"Removed your vote on {submission.quest_title}!")

    # ---- untrack ----
    async def untrack_submission(self, message_id):
        submission = await RewardSubmission.from_id(self.bot.mdb, message_id)
        await submission.untrack(self.bot.mdb)
        author = self.bot.get_user(submission.author)
        await author.send(f"I have untracked rewards submissions for {submission.quest_title}.")

    # ---- scheduled notifications ----
    async def do_notification(self, no_ping=False, destination=None):
        if not no_ping:
            ping_string = ' '.join(f"<@&{i}>" for i in constants.ROLES_TO_PING)
        else:
            ping_string = None
        channel = destination or self.bot.get_channel(constants.DISCUSSION_CHANNEL)
        embed = discord.Embed(title="Daily Rewards Update")
        open_rewards = await RewardSubmission.all(self.bot.mdb)
        nums = len(open_rewards)
        now = datetime.datetime.now()

        embed.description = f"There {'is' if nums == 1 else 'are'} {'no' if not nums else str(nums)} " \
                            f"open reward submission{'' if nums == 1 else 's'}."

        for submission in open_rewards:
            submit_time = submission.time_last_edited + datetime.timedelta(hours=24)
            details = [f"<@{submission.author}>", f"**Submitted**: {date.duration(submission.time_submitted)}"]
            if submission.time_last_edited != submission.time_submitted:
                details.append(f"**Last Edited**: {date.duration(submission.time_last_edited)}")

            details.append(f"**Votes**: {submission.upvotes} :thumbsup: | {submission.downvotes} :thumbsdown: | "
                           f"{submission.comments} :raised_hand:")

            in_time = ""
            if not now > submit_time:
                in_time = f" in {date.duration(submit_time)}"
            if submission.downvotes or submission.comments or not submission.upvotes:
                if submission.upvotes and submission.upvotes >= 3 * submission.downvotes:  # no dividing by 0
                    status = f"can reward{in_time}*"
                else:
                    status = "needs discussion"
            else:
                status = f"can reward{in_time}"
            details.append(f"**Status**: {status}")

            details.append(f"[Jump to Post](https://discordapp.com/channels/{constants.GUILD_ID}/"
                           f"{constants.REWARDS_CHANNEL}/{submission.message_id})")

            embed.add_field(name=submission.quest_title, value='\n'.join(details))

        await channel.send(content=ping_string, embed=embed)


def setup(bot):
    bot.add_cog(Rewards(bot))
