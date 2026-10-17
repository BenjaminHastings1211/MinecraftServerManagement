import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event


class StatsCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!stats$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT mc_name, death_count, playtime_seconds, session_seconds
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.id, self.player],
        ).first()

        if result is None:
            return

        playtime = (result["playtime_seconds"] or 0) + result["session_seconds"]
        current_session = result["session_seconds"]

        self.server.notify(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("☠ Death Count: ", color="#aaaaaa")
            .text(str(result["death_count"] or 0), bold=True, color="#ff5555")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("⌛ Total Playtime: ", color="#aaaaaa")
            .text(tellraw.duration(playtime), bold=True, color="#55aaff")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                tellraw.duration(current_session)
                if result["session_seconds"] > 0
                else "Not in session",
                bold=True,
                color="#ffaa00",
            )
        )

    @staticmethod
    def get_details():
        return "Shows your death count and total playtime for this server."

    @staticmethod
    def get_command():
        return "!stats"