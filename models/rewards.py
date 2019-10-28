import datetime
from enum import Enum


class Opinion(Enum):
    DOWNVOTE = -1
    COMMENT = 0
    UPVOTE = 1


class RewardSubmission:
    # construction
    def __init__(self, title: str, time_submitted: datetime.datetime, time_last_edited: datetime.datetime, author: int,
                 message_id: int, votes: list, **_):
        self.quest_title = title
        self.time_submitted = time_submitted
        self.time_last_edited = time_last_edited
        self.author = author
        self.message_id = message_id
        self.votes = votes

        self._upvotes = None
        self._downvotes = None
        self._comments = None

    @classmethod
    def new(cls, title, message):
        now = datetime.datetime.now()
        return cls(title, now, now, message.author.id, message.id, [])

    @classmethod
    async def from_id(cls, mdb, message_id):
        raw = await mdb.rewards.find_one({"message_id": message_id})
        if raw is None:
            raise SubmissionException("Reward submission not found.")
        return cls.from_dict(raw)

    @staticmethod
    async def all(mdb):
        return list(map(RewardSubmission.from_dict, await mdb.rewards.find({}).to_list(None)))

    @classmethod
    def from_dict(cls, d):
        d['votes'] = [Vote.from_dict(v) for v in d['votes']]
        return cls(**d)

    def to_dict(self):
        votes = [v.to_dict() for v in self.votes]
        return {
            "title": self.quest_title, "time_submitted": self.time_submitted, "time_last_edited": self.time_last_edited,
            "author": self.author, "message_id": self.message_id, "votes": votes
        }

    # database
    async def commit(self, mdb):
        await mdb.rewards.update_one(
            {"message_id": self.message_id},
            {"$set": self.to_dict()},
            upsert=True
        )

    async def untrack(self, mdb):
        await mdb.rewards.delete_one(
            {"message_id": self.message_id}
        )

    # props
    @property
    def upvotes(self):
        if self._upvotes is None:
            self._calculate_votes()
        return self._upvotes

    @property
    def downvotes(self):
        if self._downvotes is None:
            self._calculate_votes()
        return self._downvotes

    @property
    def comments(self):
        if self._comments is None:
            self._calculate_votes()
        return self._comments

    # methods
    def _calculate_votes(self):
        self._upvotes = 0
        self._downvotes = 0
        self._comments = 0
        for vote in self.votes:
            if vote.opinion == Opinion.UPVOTE:
                self._upvotes += 1
            elif vote.opinion == Opinion.DOWNVOTE:
                self._downvotes += 1
            else:
                self._comments += 1


class Vote:
    # construction
    def __init__(self, author: int, opinion: Opinion, timestamp: datetime.datetime):
        self.author = author
        self.opinion = opinion
        self.timestamp = timestamp

    @classmethod
    def new(cls, author, opinion):
        now = datetime.datetime.now()
        return cls(author, opinion, now)

    @classmethod
    def from_dict(cls, d):
        d['opinion'] = Opinion(d['opinion'])
        return cls(**d)

    def to_dict(self):
        return {
            "author": self.author, "opinion": self.opinion.value, "timestamp": self.timestamp
        }


class SubmissionException(Exception):
    pass
