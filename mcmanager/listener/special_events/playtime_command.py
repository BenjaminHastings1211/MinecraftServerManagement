import re

from mcmanager import tellraw
from mcmanager.listener.base import Event, duration


class PlaytimeCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!playtime$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT playtime_seconds, session_start
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player],
        ).first()

        if result is None:
            return

        playtime = result["playtime_seconds"] or 0
        session_start = result["session_start"]
        current_session = 0

        if session_start is not None:
            current_session = max(
                0,
                int((self.when - session_start).total_seconds()),
            )
            playtime += current_session

        self.server.tell(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("⌛ Total Playtime: ", color="#aaaaaa")
            .text(duration(playtime), bold=True, color="#55aaff")
        )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                duration(current_session)
                if session_start is not None
                else "Not in session",
                bold=True,
                color="#ffaa00",
            )
        )

    @staticmethod
    def get_details():
        return "Shows your total playtime and current session time for this server."

    @staticmethod
    def get_command():
        return "!playtime"
