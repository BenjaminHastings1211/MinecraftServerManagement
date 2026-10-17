import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event


class TopCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!top$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        # Fetch the top players based on playtime and death count
        top_players = db.query(
            """
            SELECT mc_name, playtime_seconds, death_count
            FROM players
            WHERE server_id = %s
            ORDER BY playtime_seconds DESC, death_count ASC
            LIMIT 10;
            """,
            [self.server.id],
        ).all()

        if not top_players:
            self.server.notify(
                tellraw.to_player(self.player).text("No player data available.")
            )
            return

        self.server.notify(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        for rank, player in enumerate(top_players, start=1):
            self.server.notify(
                tellraw.to_player(self.player)
                .text(f"{rank}. ", color="#aaaaaa")
                .text(player["mc_name"], bold=True, color="#55aaff")
                .text(f" - Playtime: {self.duration(player['playtime_seconds'])}, Deaths: {player['death_count']}", color="#aaaaaa")
            )

    @staticmethod
    def get_details():
        return "Shows the leaderboard of the top players on this server based on playtime and death count."
    
    @staticmethod
    def get_command():
        return "!top"