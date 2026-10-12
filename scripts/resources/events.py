"""
Sorting server log lines into events, each with an action().

    event = events.classify(server, line)   # Login, Logout, Chat or None

    if event:
        event.action()

To handle a new kind of message, subclass Event with a `pattern`
(a regex matched against LogLine.message) and an action(), then add
it to EVENTS. Named groups in the pattern are available as
event.match["name"].
"""

from datetime import datetime, timedelta

from resources import players, locations, tellraw
from resources.database import query
from resources.console import CHAT, JOINED, LEFT, PLAYTIME_COMMAND, DEATH, DEATH_LOCATION_COMMAND

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
        self.line = line      # the full LogLine
        self.match = match

    def __repr__(self):
        return f"{type(self).__name__}({self.line.raw!r})"

    @classmethod
    def parse(cls, server, line):
        """An instance of this event if the line matches, else None."""
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
            now.date(), datetime.strptime(self.line.time, "%H:%M:%S").time()
        )

        if moment > now + timedelta(minutes=1):
            moment -= timedelta(days=1)

        return moment

    def action(self):
        pass


class Login(Event):
    pattern = JOINED

    @property
    def player(self):
        return self.match["player"]

    def action(self):
        first_visit = players.get(self.server.number, self.player) is None

        # Record the login before messaging, so a failed message can't lose it.
        player_info = players.login(self.server.number, self.player, at=self.when)

        if first_visit:
            self.server.register_player(self.player)

        # set the death counter to match db
        self.server.command("scoreboard players set %s deaths %d"%(self.player,player_info["death_count"]))

        # self.server.tell(            
        #     tellraw.to_player(self.player)
        #     .text("Welcome ", bold=True, color="red")
        #     .text(self.player, color="aqua")
        #     .text("!")
        # )


class Logout(Event):
    pattern = LEFT

    @property
    def player(self):
        return self.match["player"]

    def action(self):
        players.logout(self.server.number, self.player, at=self.when)


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

    # override the existing parse to also check with the db and server for death information
    @classmethod
    def parse(cls, server, line):
        event = super().parse(server, line)

        if event is None:
            return None

        player = event.player

        current_count = server.get_death_count(player)

        # Read the last stored count from your database.
        result = query(
            """
            SELECT death_count
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [server.number, player]
        ).first()

        if result is None:
            return None        

        previous_count = result["death_count"] or 0

        if current_count <= previous_count:
            return None


        return event

    @property
    def player(self):
        return self.match["player"]

    @property
    def by_entity(self):
        return self.match.groupdict().get("by")

    def action(self):
        result = query(
            """
            SELECT death_count, last_death_date
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player]
        ).first()

        death_count = result['death_count']
        last_death_date = result['last_death_date']

        if last_death_date is not None:
            # has died before
            seconds_since_last_death = int((datetime.now() - last_death_date).total_seconds())

            self.server.tell(
                tellraw.to_all()
                .text("last death: ")
                .text(duration(seconds_since_last_death))
                .text(" ago")
            )

        self.server.tell(
            tellraw.to_player(self.player)
            .text("Use '")
            .text("!find death", color="aqua")
            .text("' to get location of death.")
        )

        query(
            """
                UPDATE players
                SET death_count = death_count + 1,
                last_death_date = NOW()
                WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player]
        )

        # get death info and add it as a location
        pos = self.server.get_player_pos(self.player)
        dim = self.server.get_player_dimension(self.player)

        # create the location
        db_player_info = players.get(self.server.number, self.player)
        locations.create(self.server.number, db_player_info['id'], "%s death location"%self.player, pos, dim);


class DeathLocationCommand(Event):
    pattern = DEATH_LOCATION_COMMAND

    @property
    def player(self):
        return self.match["player"]

    def action(self):
        db_player_info = players.get(self.server.number, self.player)
        result = locations.get(self.server.number, db_player_info['id'], "%s death location"%self.player);

        if result is None:
            self.server.tell(tellraw.to_player(self.player).text("No death location."))
            return;
        
        self.server.tell(
            tellraw.to_player(self.player)
            .text(result['dimension'], bold=True, color="#00ff00")
            .text(": ")
            .text(result['x_position'], bold=True, color="#ff0000")
            .text(" ")
            .text(result['y_position'], bold=True, color="#ff0000")
            .text(" ")
            .text(result['z_position'], bold=True, color="#ff0000")
        )


class PlaytimeCommand(Event):
    pattern = PLAYTIME_COMMAND

    @property
    def player(self):
        return self.match["player"]

    @property
    def text(self):
        return self.match["text"]

    def action(self):
        result = query(
            """
            SELECT playtime_seconds, session_start
            FROM players
            WHERE server_id = %s AND mc_name = %s;
            """,
            [self.server.number, self.player]
        ).first()

        playtime = result["playtime_seconds"] or 0
        session_start = result["session_start"]
        current_session = 0

        if session_start is not None:
            current_session = max(
                0, int((self.when - session_start).total_seconds())
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
                duration(current_session) if session_start is not None else "Not in session",
                bold=True,
                color="#ffaa00"
            )
        )


EVENTS = [Login, Logout, Death, DeathLocationCommand, PlaytimeCommand, Chat]


def classify(server, line):
    """The first event in EVENTS that matches the line, or None."""
    for event_class in EVENTS:
        event = event_class.parse(server, line)

        if event is not None:
            return event

    return None
