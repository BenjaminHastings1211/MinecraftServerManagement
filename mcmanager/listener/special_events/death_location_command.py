import re

from mcmanager.messages import tellraw
from mcmanager.database import players, locations, permissions
from mcmanager.listener.base import Event


class DeathLocationCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!find death$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        db_player_info = players.get(
            db,
            self.server.id,
            self.player,
        )

        if db_player_info is None:
            self.server.notify(
                tellraw.to_player(self.player).text("No death location.")
            )
            return

        result = locations.get(
            db,
            self.server.id,
            db_player_info["id"],
            f"{self.player} death location",
        )

        if result is None:
            self.server.notify(
                tellraw.to_player(self.player).text("No death location.")
            )
            return

        self.server.notify(
            tellraw.to_player(self.player)
            .text(result["dimension"], bold=True, color="#00ff00")
            .text(": ")
            .text(result["x_position"], bold=True, color="#ff0000")
            .text(" ")
            .text(result["y_position"], bold=True, color="#ff0000")
            .text(" ")
            .text(result["z_position"], bold=True, color="#ff0000")
        )

    @staticmethod
    def get_details():
        return "Shows the coordinates of your last death on this server."

    @staticmethod
    def get_command():
        return "!find death"
