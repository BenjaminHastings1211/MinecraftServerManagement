import re

from mcmanager.messages import tellraw
from mcmanager.listener.base import Event, duration, seconds_since


class StatsCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> !stats$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT
                p.uuid,
                p.mc_name,
                p.death_count,
                p.playtime_seconds,
                p.last_death_date,
                p.message_count,
                COALESCE((
                    SELECT TIMESTAMPDIFF(SECOND, s.started_at, NOW())
                    FROM sessions s
                    WHERE s.player_id = p.id
                      AND s.ended_at IS NULL
                    ORDER BY s.started_at DESC
                    LIMIT 1
                ), 0) AS current_session_seconds
            FROM players p
            WHERE p.server_id = %s
              AND p.mc_name = %s
            """,
            [self.server.id, self.player],
        ).first()

        if result is None:
            return

        player_uuid = result["uuid"]
        service = self.server.statsService

        current_session = result["current_session_seconds"] or 0
        playtime = (result["playtime_seconds"] or 0) + current_session
        message_count = result["message_count"] or 0

        # Retrieve Minecraft statistics through the stats service.
        stats_available = player_uuid is not None and service.get(player_uuid) is not None

        mobs_killed = service.get_mobs_killed(player_uuid) if stats_available else None
        blocks_mined = service.get_blocks_mined(player_uuid) if stats_available else None
        distance_km = service.get_distance_traveled_km(player_uuid) if stats_available else None
        fish_caught = service.get_fish_caught(player_uuid) if stats_available else None
        animals_bred = service.get_animals_bred(player_uuid) if stats_available else None
        villager_trades = service.get_villager_trades(player_uuid) if stats_available else None

        since_death = seconds_since(result["last_death_date"])

        unavailable = "Data not available"

        stats = [
            ("☠ Death Count", result["death_count"] or 0, "#ff5555"),
            ("⌛ Total Playtime", duration(playtime), "#55aaff"),
            (
                "▶ Current Session",
                duration(current_session) if current_session > 0 else "Not in session",
                "#ffaa00",
            ),
            (
                "⛏ Total Blocks Mined",
                f"{blocks_mined:,}" if blocks_mined is not None else unavailable,
                "#55ff55",
            ),
            (
                "⚔ Total Mob Kills",
                f"{mobs_killed:,}" if mobs_killed is not None else unavailable,
                "#ff5555",
            ),
            (
                "➤ Distance Traveled",
                f"{distance_km:,.1f} km" if distance_km is not None else unavailable,
                "#55ffff",
            ),
            ("✉ Messages Sent", f"{message_count:,}", "#ffff55"),
            (
                "♥ Since Last Death",
                duration(since_death) if since_death is not None else unavailable,
                "#ff7777",
            ),
            (
                "≈ Fish Caught",
                f"{fish_caught:,}" if fish_caught is not None else unavailable,
                "#55aaff",
            ),
            (
                "✿ Animals Bred",
                f"{animals_bred:,}" if animals_bred is not None else unavailable,
                "#ff55ff",
            ),
            (
                "⚖ Villager Trades",
                f"{villager_trades:,}" if villager_trades is not None else unavailable,
                "#55ff55",
            ),
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
            self.construct_stat_readout(message, title, value, color, last_line=(i == len(stats) - 1));

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