import datetime
from typing import List, Optional

from bson import ObjectId


class Game:
    def __init__(self, _id: Optional[ObjectId], title: str, dm: int, message_id: int,
                 time: datetime.datetime = None, players: List[int] = None):
        if players is None:
            players = []

        self._id = _id
        self.title = title
        self.dm = dm
        self.message_id = message_id

        self.time = time
        self.players = players

    @classmethod
    def new(cls, message, title, time=None):
        return cls(None, title, message.author.id, message.id, time)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def to_dict(self):
        return {
            "title": self.title, "dm": self.dm, "message_id": self.message_id,
            "time": self.time, "players": self.players
        }
