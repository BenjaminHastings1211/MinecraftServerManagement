import re

from mcmanager.listener.base import Event
from mcmanager.database import players


class Logout(Event):
    # Newer versions prefix leaves with "System chat: ".
    pattern = re.compile(
        r"^(?:System chat: )?(?P<player>\w+)(?: left the game| lost connection: .*)$"
    )

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        players.logout(
            db,
            self.server.id,
            self.player,
            at=self.when,
        )
