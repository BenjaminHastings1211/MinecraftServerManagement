"""
Sorting server log lines into events, each with an action().

    with server.db as db:
        event = events.classify(server, line, db)

        if event:
            event.action(db)

To handle a new kind of message, subclass Event with a `pattern`
(a regex matched against LogLine.message) and an action(), then add
it to EVENTS. Named groups in the pattern are available as
event.match["name"].
"""

from datetime import datetime, timedelta
from resources.database import players, locations
from resources import tellraw
from resources.console import (
    CHAT,
    JOINED,
    LEFT,
    PLAYTIME_COMMAND,
    DEATH,
    DEATH_LOCATION_COMMAND,
)


def duration(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not days:
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"


class Event:
    pattern = None

    def __init__(self, server, line, match):
        self.server = server
        self.line = line
        self.match = match

    def __repr__(self):
        return f"{type(self).__name__}({self.line.raw!r})"

    @classmethod
    def parse(cls, server, line, db):
        """Return an event instance if the line matches, otherwise None."""
        # Only the server's own messages, so a player can't fake one in chat.
        if line.source != "Server thread":
            return None

        match = cls.pattern.match(line.message)
        return cls(server, line, match) if match else None

    @property
    def when(self):
        """
        The line's time as a datetime. Logs only give the time of day,
        so it's taken to be today, or yesterday if that would put it
        in the future (a line from just before midnight).
        """
        now = datetime.now()
        moment = datetime.combine(
            now.date(),
            datetime.strptime(self.line.time, "%H:%M:%S").time(),
        )

        if moment > now + timedelta(minutes=1):
            moment -= timedelta(days=1)

        return moment

    def action(self, db):
        pass


class Login(Event):
    pattern = JOINED

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        first_visit = (
            players.get(db, self.server.number, self.player) is None
        )

        # Record the login before messaging, so a failed message can't lose it.
        player_info = players.login(
            db,
            self.server.number,
            self.player,
            at=self.when,
        )

        if first_visit:
            self.server.register_player(self.player)

        # Keep the Minecraft scoreboard synchronized with the database.
        self.server.command(
            "scoreboard players set %s deaths %d"
            % (self.player, player_info["death_count"])
        )


class Logout(Event):
    pattern = LEFT

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        players.logout(
            db,
            self.server.number,
            self.player,
            at=self.when,
        )


class Chat(Event):
    pattern = CHAT

    @property
    def player(self):
        return self.match["player"]

    @property
    def text(self):
        return self.match["text"]


class Death(Event):
    pattern = DEATH

    @classmethod
    def parse(cls, server, line, db):
        event = super().parse(server, line, db)

        if event is None:
            return None

        # Compare Minecraft's death scoreboard with the database.
        current_count = server.get_death_count(event.player)

        result = db.query(
            """
            SELECT death_count
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [server.number, event.player],
        ).first()

        if result is None:
            return None

        previous_count = result["death_count"] or 0

        # Ignore death messages that do not correspond to a new death.
        if current_count <= previous_count:
            return None

        return event

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        result = db.query(
            """
            SELECT last_death_date
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player],
        ).first()

        if result is None:
            return

        last_death_date = result["last_death_date"]

        if last_death_date is not None:
            seconds_since_last_death = max(
                0,
                int((self.when - last_death_date).total_seconds()),
            )

            self.server.tell(
                tellraw.to_all()
                .text("Last death: ")
                .text(duration(seconds_since_last_death))
                .text(" ago")
            )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("Use '")
            .text("!find death", color="aqua")
            .text("' to get location of death.")
        )

        # Update death information in the database.
        db.query(
            """
            UPDATE players
            SET death_count = death_count + 1,
                last_death_date = %s
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.when, self.server.number, self.player],
        )

        # Get death information and save it as a waypoint.
        pos = self.server.get_player_pos(self.player)
        dim = self.server.get_player_dimension(self.player)

        db_player_info = players.get(
            db,
            self.server.number,
            self.player,
        )

        if db_player_info is not None:
            locations.create(
                db,
                self.server.number,
                db_player_info["id"],
                f"{self.player} death location",
                pos,
                dim,
            )


class DeathLocationCommand(Event):
    pattern = DEATH_LOCATION_COMMAND

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        db_player_info = players.get(
            db,
            self.server.number,
            self.player,
        )

        if db_player_info is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No death location.")
            )
            return

        result = locations.get(
            db,
            self.server.number,
            db_player_info["id"],
            f"{self.player} death location",
        )

        if result is None:
            self.server.tell(
                tellraw.to_player(self.player).text("No death location.")
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


class PlaytimeCommand(Event):
    pattern = PLAYTIME_COMMAND

    @property
    def player(self):
        return self.match["player"]

    @property
    def text(self):
        return self.match["text"]

    def action(self, db):
        result = db.query(
            """
            SELECT playtime_seconds, session_start
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player],
        ).first()

        if result is None:
            return

        playtime = result["playtime_seconds"] or 0
        session_start = result["session_start"]
        current_session = 0

        if session_start is not None:
            current_session = max(
                0,
                int((self.when - session_start).total_seconds()),
            )
            playtime += current_session

        self.server.tell(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("⌛ Total Playtime: ", color="#aaaaaa")
            .text(duration(playtime), bold=True, color="#55aaff")
        )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("▶ Current Session: ", color="#aaaaaa")
            .text(
                duration(current_session)
                if session_start is not None
                else "Not in session",
                bold=True,
                color="#ffaa00",
            )
        )


EVENTS = [
    Login,
    Logout,
    Death,
    DeathLocationCommand,
    PlaytimeCommand,
    Chat,
]


def classify(server, line, db):
    """Return the first event that matches the line, or None."""
    for event_class in EVENTS:
        event = event_class.parse(server, line, db)

        if event is not None:
            return event

    return None