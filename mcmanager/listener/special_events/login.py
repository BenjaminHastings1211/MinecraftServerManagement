import re

from mcmanager.listener.base import Event
from mcmanager.database import players


class Login(Event):
    # Newer versions prefix joins with "System chat: ".
    pattern = re.compile(r"^(?:System chat: )?(?P<player>\w+) joined the game$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        first_visit = (
            players.get(db, self.server.number, self.player) is None
        )

        # Record the login before messaging, so a failed message can't lose it.
        player_info = players.login(
            db,
            self.server.number,
            self.player,
            at=self.when,
        )

        if first_visit:
            self.server.register_player(self.player)

        # Keep the Minecraft scoreboard synchronized with the database.
        self.server.command(
            "scoreboard players set %s deaths %d"
            % (self.player, player_info["death_count"])
        )
