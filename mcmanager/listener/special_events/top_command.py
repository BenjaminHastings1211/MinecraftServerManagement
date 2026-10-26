import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event, duration
from mcmanager.database.sessions import playtime_summary


class TopCommand(Event):
    pattern = re.compile(
        r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> !top(?: (?P<amount>\d+) (?P<unit>DAY|DAYS|WEEK|WEEKS|MONTH|MONTHS))?$",
        re.IGNORECASE,
    )

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        amount = int(self.match["amount"] or 0)
        unit = (self.match["unit"] or "").upper()

        if amount and unit:
            # Convert weeks to days for MySQL's INTERVAL syntax.
            if unit in ("WEEK", "WEEKS"):
                amount *= 7
                unit = "DAY"

            interval = f"{amount} {unit}"
            top_players = playtime_summary(db, self.server.id, interval)[:10]
            period = f"Last {amount} {unit.lower()}"
        else:
            top_players = db.query(
                """
                SELECT mc_name, playtime_seconds, death_count
                FROM players
                WHERE server_id = %s
                ORDER BY playtime_seconds DESC, death_count ASC
                LIMIT 10
                """,
                [self.server.id],
            ).rows
            period = "All-time"

        if not top_players:
            self.server.notify(
                tellraw.to_player(self.player).text("No player data available.")
            )
            return

        message = (
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(f" — {period} Top Players ", color="#aaaaaa")
            .text("━━━", color="#555555")
            .new_line()
        )

        for rank, player in enumerate(top_players, start=1):
            if (player['playtime_seconds']) == 0:
                continue
                
            message.text(f"{rank}. ", color="#aaaaaa")
            message.text(player["mc_name"], bold=True, color="#55aaff")
            message.text(
                f" - Playtime: {duration(player['playtime_seconds'])}",
                color="#aaaaaa",
            )

            if "death_count" in player:
                message.text(
                    f", Deaths: {player['death_count']}",
                    color="#aaaaaa",
                )

            if rank < len(top_players):
                message.new_line()

        self.server.notify(message)

    @staticmethod
    def get_details():
        return "Shows the top 10 players by all-time or interval playtime."

    @staticmethod
    def get_command():
        return "!top"