import re

from mcmanager import tellraw
from mcmanager.database import players, permissions
from mcmanager.listener.base import Event


class FindCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!find (?P<target_player>\w+)$")

    permission = permissions.OP

    @property
    def player(self):
        return self.match["player"]

    @property
    def target_player(self):
        return self.match["target_player"]

    def action(self, db):
        db_target_player_info = players.get(
            db,
            self.server.id,
            self.target_player,
        )

        if db_target_player_info is None:
            self.server.notify(
                tellraw.to_player(self.player).text("Player not found")
            )
            return

        player_dimension = self.server.get_player_dimension(self.target_player)
        player_position = self.server.get_player_pos(self.target_player)

        if player_dimension is None or player_position is None:
            self.server.notify(
                tellraw.to_player(self.player).text("No location found for player.")
            )
            return

        x, y, z = (int(value) for value in player_position)

        self.server.notify(
            tellraw.to_player(self.player)
            .text(player_dimension, bold=True, color="#00ff00")
            .text(": ")
            .text(x, bold=True, color="#ff0000")
            .text(" ")
            .text(y, bold=True, color="#ff0000")
            .text(" ")
            .text(z, bold=True, color="#ff0000")
        )

    #This method will change once we implement admin checks, for now it will just return the string
    @staticmethod
    def get_details():
        return "[OP Command] Shows the coordinates of the last known location of a player on this server."

    @staticmethod
    def get_command():
        return "!find <player>"