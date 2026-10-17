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
            .text(self.duration(playtime), bold=True, color="#55aaff")
        )

        self.server.notify(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                self.duration(current_session) if current_session > 0 else "Not in session",
                bold=True,
                color="#ffaa00",
            )
        )

    @staticmethod
    def get_details():
        return "Shows your death count and total playtime for this server."

    @staticmethod
    def get_command():
        return "!stats"

    #Time Fomatting method(could add to a utils file later)
    @staticmethod
    def duration(seconds):
        """Format seconds as e.g. '2d 3h 14m', '5m 12s', or '42s'."""
        seconds = int(seconds or 0)
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)

        if days:
            return f"{days}d {hours}h {minutes}m"
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"