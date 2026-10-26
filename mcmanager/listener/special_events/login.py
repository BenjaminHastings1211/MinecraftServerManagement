import re

from mcmanager.listener.base import Event
from mcmanager.database import players, sessions, servers


class Login(Event):
    pattern = re.compile(r"^(?:System chat: )?(?P<player>\w+) joined the game$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        server_id = self.server.id
        player_name = self.player

        # Find or create the player.
        player_info = players.get(db, server_id, player_name)
        first_visit = player_info is None
        player_deaths = player_info['death_count'];

        if first_visit:
            player_info = players.create(db, server_id, player_name)

        # Determine whether the player needs reinitialization.
        reinit_after = servers.get_players_reinit_after(db, server_id)
        needs_reinit = (
            reinit_after is not None
            and not sessions.has_joined_since(
                db, player_info["id"], reinit_after
            )
        )

        # Register new players, players marked for reinitialization,
        # or existing players whose UUID is missing.
        needs_registration = (
            first_visit
            or needs_reinit
            or player_info["uuid"] is None
        )

        if needs_registration:
            self.server.register_player(db, player_name)

            # Refresh player data in case registration updated the record.
            player_info = players.get(db, server_id, player_name)

        # Synchronize playtime with Minecraft's stats.
        player_uuid = player_info["uuid"]

        if player_uuid is not None:
            self.server.statsService.reload(player_uuid)
            playtime = self.server.statsService.get_playtime_seconds(player_uuid)
            player_deaths = self.server.statsService.get_deaths(player_uuid)

            if playtime is not None:
                players.set_playtime(db, server_id, player_name, playtime)

        # Start the session after checking reinitialization history.
        sessions.start(db, server_id, player_name, at=self.when)

        # Synchronize the deaths
        players.set_death_count(db, server_id, player_name, player_deaths)
        self.server.command(
            "scoreboard players set %s deaths %d"
            % (player_name, player_deaths)
        )