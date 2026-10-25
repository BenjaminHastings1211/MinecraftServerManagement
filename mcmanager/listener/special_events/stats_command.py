
import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event, duration


class StatsCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!stats$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT
                p.mc_name,
                p.death_count,
                p.playtime_seconds,
                p.message_count,
                COALESCE((
                    SELECT TIMESTAMPDIFF(SECOND, s.started_at, NOW())
                    FROM sessions s
                    WHERE s.player_id = p.id AND s.ended_at IS NULL
                    ORDER BY s.started_at DESC
                    LIMIT 1
                ), 0) AS current_session_seconds
            FROM players p
            WHERE p.server_id = %s AND p.mc_name = %s;
            """,
            [self.server.id, self.player],
        ).first()

        if result is None:
            return

        current_session = result["current_session_seconds"] or 0
        playtime = (result["playtime_seconds"] or 0) + current_session

        player_stats = self.server.get_player_stats(db, self.player)
        mobs_killed = self.server.get_mobs_killed(db, self.player, player_stats)
        blocks_mined = self.server.get_blocks_mined(db, self.player, player_stats)

        custom = player_stats.get("minecraft:custom", {})

        distance_km = sum(
            value
            for key, value in custom.items()
            if key.endswith("_one_cm")
        ) / 100000

        message_count = result["message_count"] or 0
        since_death = custom.get("minecraft:time_since_death", 0) // 20
        fish_caught = custom.get("minecraft:fish_caught", 0)
        animals_bred = custom.get("minecraft:animals_bred", 0)
        villager_trades = custom.get("minecraft:traded_with_villager", 0)

        stats = [
            ("☠ Death Count", result["death_count"] or 0, "#ff5555"),
            ("⌛ Total Playtime", duration(playtime), "#55aaff"),
            (
                "▶ Current Session",
                duration(current_session)
                if current_session > 0
                else "Not in session",
                "#ffaa00",
            ),
            (
                "⛏ Total Blocks Mined",
                blocks_mined
                if blocks_mined is not None
                else "Data not available",
                "#55ff55",
            ),
            (
                "⚔ Total Mob Kills",
                mobs_killed
                if mobs_killed is not None
                else "Data not available",
                "#ff5555",
            ),
            ("➤ Distance Traveled", f"{distance_km:,.1f} km", "#55ffff"),
            ("✉ Messages Sent", f"{message_count:,}", "#ffff55"),
            ("♥ Since Last Death", duration(since_death), "#ff7777"),
            ("≈ Fish Caught", f"{fish_caught:,}", "#55aaff"),
            ("✿ Animals Bred", f"{animals_bred:,}", "#ff55ff"),
            ("⚖ Villager Trades", f"{villager_trades:,}", "#55ff55"),
        ]

        message = tellraw.to_player(self.player)
        (
            message
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
            .new_line()
        )

        for i, (title, value, color) in enumerate(stats):
            self.construct_stat_readout(message, title, value, color, last_line=(i == len(stats) - 1))

        self.server.notify(message)

    @staticmethod
    def construct_stat_readout(message, title, value, accent_color="#00FF00", last_line=False):
        message.text(f"{title}: ", color="#aaaaaa")
        message.text(str(value), bold=True, color=accent_color)
        if not last_line:
            message.new_line()

    @staticmethod
    def get_details():
        return "Shows your statistics for this server."

    @staticmethod
    def get_command():
        return "!stats"