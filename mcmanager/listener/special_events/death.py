import re

from mcmanager import server, tellraw
from mcmanager.database import players, locations
from mcmanager.listener.base import Event, duration


class Death(Event):
    # Newer versions prefix death messages with "System chat: ".
    pattern = re.compile(r"^(?:System chat: )?(?P<player>\w+)(?:\s.*)?$")

    @classmethod
    def parse(cls, server, line, db):
        event = super().parse(server, line, db)

        if event is None:
            return None

        result = db.query(
            """
            SELECT death_count
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [server.number, event.player],
        ).first()

        if result is None:
            return None

        previous_count = result["death_count"] or 0

        # Compare Minecraft's death scoreboard with the database.
        current_count = server.get_death_count(event.player)

        # Ignore death messages that do not correspond to a new death.
        if current_count <= previous_count:
            return None

        return event

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT last_death_date
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player],
        ).first()

        if result is None:
            return

        last_death_date = result["last_death_date"]

        if last_death_date is not None:
            seconds_since_last_death = max(
                0,
                int((self.when - last_death_date).total_seconds()),
            )

            self.server.tell(
                tellraw.to_all()
                .text("Last death: ")
                .text(duration(seconds_since_last_death))
                .text(" ago")
            )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("Use '")
            .text("!find death", color="aqua")
            .text("' to get location of death.")
        )

        # Update death information in the database.
        db.query(
            """
            UPDATE players
            SET death_count = death_count + 1,
                last_death_date = %s
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.when, self.server.number, self.player],
        )

        # Get death information and save it as a waypoint.
        pos = self.server.get_player_pos(self.player)
        dim = self.server.get_player_dimension(self.player)

        db_player_info = players.get(
            db,
            self.server.number,
            self.player,
        )

        if db_player_info is not None:
            locations.create(
                db,
                self.server.number,
                db_player_info["id"],
                f"{self.player} death location",
                pos,
                dim,
            )
