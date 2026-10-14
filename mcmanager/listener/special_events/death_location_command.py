import re

from mcmanager import tellraw
from mcmanager.database import players, locations
from mcmanager.listener.base import Event


class DeathLocationCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!find death$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        db_player_info = players.get(
            db,
            self.server.number,
            self.player,
        )

        if db_player_info is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No death location.")
            )
            return

        result = locations.get(
            db,
            self.server.number,
            db_player_info["id"],
            f"{self.player} death location",
        )

        if result is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No death location.")
            )
            return

        self.server.tell(
            tellraw.to_player(self.player)
            .text(result["dimension"], bold=True, color="#00ff00")
            .text(": ")
            .text(result["x_position"], bold=True, color="#ff0000")
            .text(" ")
            .text(result["y_position"], bold=True, color="#ff0000")
            .text(" ")
            .text(result["z_position"], bold=True, color="#ff0000")
        )

    def get_details(self):
        return "!find death - Shows the coordinates of your last death on this server."
