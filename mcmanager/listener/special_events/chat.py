import re

from mcmanager.listener.base import Event


class Chat(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> (?P<text>.*)$")

    @property
    def player(self):
        return self.match["player"]

    @property
    def text(self):
        return self.match["text"]

    def action(self, db):
        increment_message_count(db, self.server, self.player)
