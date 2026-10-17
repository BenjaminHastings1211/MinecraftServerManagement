import re

from mcmanager.listener.base import Event
from mcmanager.database import sessions


class Logout(Event):
    pattern = re.compile(
        r"^(?:System chat: )?(?P<player>\w+)(?: left the game| lost connection: .*)$"
    )

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        sessions.end(db, self.server.id, self.player, at = self.when)
