import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event, duration
from mcmanager.database import players


class PlaytimeCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!playtime$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = players.get(db, self.server.id, self.player)

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
            .text("⌛ Total Playtime: ", color="#aaaaaa")
            .text(duration(playtime), bold=True, color="#55aaff")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                duration(current_session) if result["online"] else "Not in session",
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
