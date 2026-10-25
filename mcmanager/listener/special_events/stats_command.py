import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event


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

        stats = self.server.get_player_stats(self.player)
        mobs_killed = self.server.get_mobs_killed(self.player, stats)
        blocks_mined = self.server.get_blocks_mined(self.player, stats)

        custom = stats.get("minecraft:custom", {})

        distance_km = sum(
            value for key, value in custom.items() if key.endswith("_one_cm")
        ) / 100000
        message_count = result["message_count"] or 0
        since_death = custom.get("minecraft:time_since_death", 0) // 20
        fish_caught = custom.get("minecraft:fish_caught", 0)
        animals_bred = custom.get("minecraft:animals_bred", 0)
        villager_trades = custom.get("minecraft:traded_with_villager", 0)

        self.server.notify(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("☠ Death Count: ", color="#aaaaaa")
            .text(str(result["death_count"] or 0), bold=True, color="#ff5555")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("⌛ Total Playtime: ", color="#aaaaaa")
            .text(tellraw.duration(playtime), bold=True, color="#55aaff")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                tellraw.duration(current_session) if current_session > 0 else "Not in session",
                bold=True,
                color="#ffaa00",
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("⛏ Total Blocks Mined: ", color="#aaaaaa")
            .text(
                str(blocks_mined) if blocks_mined is not None else "Data not available",
                bold=True,
                color="#55ff55",
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("⚔ Total Mob Kills: ", color="#aaaaaa")
            .text(
                str(mobs_killed) if mobs_killed is not None else "Data not available",
                bold=True,
                color="#ff5555",
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("➤ Distance Traveled: ", color="#aaaaaa")
            .text(
                str(f"{distance_km:,.1f} km") if distance_km is not None else "Data not available",
                bold=True,
                color="#55ffff"
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("✉ Messages Sent: ", color="#aaaaaa")
            .text(
                str(f"{message_count:,}") if message_count is not None else "Data not available",
                bold=True,
                color="#ffff55"
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("♥ Since Last Death: ", color="#aaaaaa")
            .text(
                tellraw.duration(since_death) if since_death is not None else "Data not available",
                bold=True,
                color="#ff7777"
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("≈ Fish Caught: ", color="#aaaaaa")
            .text(
                str(f"{fish_caught:,}") if fish_caught is not None else "Data not available",
                bold=True,
                color="#55aaff"
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("✿ Animals Bred: ", color="#aaaaaa")
            .text(
                str(f"{animals_bred:,}") if animals_bred is not None else "Data not available",
                bold=True,
                color="#ff55ff"
            )
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("⚖ Villager Trades: ", color="#aaaaaa")
            .text(
                str(f"{villager_trades:,}") if villager_trades is not None else "Data not available",
                bold=True,
                color="#55ff55"
            )
        )

    @staticmethod
    def get_details():
        return "Shows your statistics for this server."

    @staticmethod
    def get_command():
        return "!stats"