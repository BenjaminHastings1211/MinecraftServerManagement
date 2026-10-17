import re

from mcmanager.listener.base import Event
from mcmanager.database import players, sessions


class Login(Event):
    pattern = re.compile(r"^(?:System chat: )?(?P<player>\w+) joined the game$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        first_visit = (
            players.get(db, self.server.id, self.player) is None
        )

        # create & initalize player if it is first time on server
        player_info = players.create(db, self.server.id, self.player, first_joined=self.when)
        if first_visit:
            self.server.register_player(self.player)

        # create the session
        sessions.start(db, self.server.id, self.player, at = self.when)

        # Keep the Minecraft scoreboard synchronized with the database.
        self.server.command(
            "scoreboard players set %s deaths %d"
            % (self.player, player_info["death_count"])
        )
