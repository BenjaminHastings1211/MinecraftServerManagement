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

        player_dimension = self.server.get_player_dimension(self.target_player)
        player_position = self.server.get_player_position(self.target_player)

        if player_dimension is None or player_position is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No location found for player.")
            )
            return

        self.server.tell(
            tellraw.to_player(self.player)
            .text(player_dimension, bold=True, color="#00ff00")
            .text(": ")
            .text(player_position["x"], bold=True, color="#ff0000")
            .text(" ")
            .text(player_position["y"], bold=True, color="#ff0000")
            .text(" ")
            .text(player_position["z"], bold=True, color="#ff0000")
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