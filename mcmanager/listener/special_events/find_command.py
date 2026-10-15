import re

from mcmanager import tellraw
from mcmanager.database import players, locations
from mcmanager.listener.base import Event


class FindCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!find (?P<target_player>\w+)$")

    @property
    def player(self):
        return self.match["player"]

    @property
    def target_player(self):
        return self.match["target_player"]

    def action(self, db):
        db_target_player_info = players.get(
            db,
            self.server.number,
            self.target_player,
        )

        if db_target_player_info is None:
            self.server.tell(
                tellraw.to_player(self.player).text("Player not found")
            )
            return

        result = locations.get(
            db,
            self.server.number,
            db_target_player_info["id"],
            f"{self.target_player} location",
        )

        if result is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No location found for player.")
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

    @staticmethod
    def get_details():
        #if self.is_admin:
            return "|Admin Command| Shows the coordinates of the last known location of a player on this server."
        #else:
            return

    @staticmethod
    def get_command():
        return "!find <player>"