import re

from mcmanager.listener.base import Event
from mcmanager.database import sessions, players


class Logout(Event):
    pattern = re.compile(
        r"^(?:System chat: )?(?P<player>\w+)(?: left the game| lost connection: .*)$"
    )

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        player_info = players.get(db, self.server.id, self.player)

        # remove stats from cache
        self.server.statsService.unload(player_info["uuid"])

        sessions.end(db, self.server.id, self.player, at = self.when)
