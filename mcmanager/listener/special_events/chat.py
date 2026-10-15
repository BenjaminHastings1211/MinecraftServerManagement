import re

from mcmanager.listener.base import Event
from mcmanager.database import players


class Chat(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> (?P<text>.*)$")

    @property
    def player(self):
        return self.match["player"]

    @property
    def text(self):
        return self.match["text"]

    def action(self, db):
        players.increment_message_count(db, self.server.id, self.player)
