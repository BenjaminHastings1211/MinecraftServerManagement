import re

from mcmanager import tellraw
from mcmanager.database import players, permissions
from mcmanager.listener.base import Event


class PermCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!perm(?: (?P<target_player>\w+))?$")

    # Lowest permission level, so every player can run the command.
    # Viewing other players is gated inside action().
    permission = permissions.PLAYER

    @property
    def player(self):
        return self.match["player"]

    @property
    def target_player(self):
        return self.match["target_player"]

    @staticmethod
    def _level_name(level):
        return getattr(level, "name", str(level))

    def action(self, db):
        db_player_info = players.get(
            db,
            self.server.id,
            self.player,
        )

        if db_player_info is None:
            self.server.notify(
                tellraw.to_player(self.player).text("Player not found")
            )
            return

        # !perm -> own level, available to everyone
        if self.target_player is None or self.target_player.lower() == self.player.lower():
            self.server.notify(
                tellraw.to_player(self.player)
                .text("Your permission level: ")
                .text(self._level_name(db_player_info["permission_id"]), bold=True, color="#00ff00")
            )
            return

        # Everything below is OP and above only
        if db_player_info["permission_id"] < permissions.OP:
            self.server.notify(
                tellraw.to_player(self.player).text("You can only view your own permission level.")
            )
            return

        # !perm all -> list every player
        if self.target_player.lower() == "all":
            all_players = players.online(db, self.server.id)

            if not all_players:
                self.server.notify(
                    tellraw.to_player(self.player).text("No players found.")
                )
                return

            message = tellraw.to_player(self.player)
            for index, info in enumerate(sorted(all_players, key=lambda p: p["mc_name"].lower())):
                if index > 0:
                    message = message.text(" | ")
                message = (
                    message
                    .text(info["mc_name"], bold=True, color="#00ff00")
                    .text(": ")
                    .text(self._level_name(info["permission_id"]), bold=True, color="#ff0000")
                )

            self.server.notify(message)
            return

        # !perm <player> -> one player's level
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

        self.server.notify(
            tellraw.to_player(self.player)
            .text(self.target_player, bold=True, color="#00ff00")
            .text(": ")
            .text(self._level_name(db_target_player_info.permission), bold=True, color="#ff0000")
        )

    @staticmethod
    def get_details():
        return "Shows your permission level. OPs and admins can also view another player's level, or all players with !perm all."

    @staticmethod
    def get_command():
        return "!perm [player|all]"