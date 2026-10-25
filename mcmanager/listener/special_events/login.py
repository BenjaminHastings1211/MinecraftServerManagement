import re

from mcmanager.listener.base import Event
from mcmanager.database import players, sessions, servers


class Login(Event):
    pattern = re.compile(r"^(?:System chat: )?(?P<player>\w+) joined the game$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        player_info = players.get(db, self.server.id, self.player)
        first_visit = player_info is None

        reinit_after = servers.get_players_reinit_after(db, self.server.id)
        needs_reinit = (
            reinit_after is not None
            and (
                first_visit
                or not sessions.played_since(
                    db, player_info["id"], reinit_after
                )
            )
        )

        # Create the player if they don't exist yet.
        player_info = players.create(db, self.server.id, self.player)

        # Initialize new players or players marked for reinitialization.
        if first_visit or needs_reinit:
            self.server.register_player(db, self.player)

        # Create the session after checking the previous session history.
        sessions.start(db, self.server.id, self.player, at=self.when)

        # Keep the Minecraft scoreboard synchronized with the database.
        self.server.command(
            "scoreboard players set %s deaths %d"
            % (self.player, player_info["death_count"])
        )