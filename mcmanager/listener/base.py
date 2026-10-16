"""
The Event base class that every event in special_events/ subclasses,
plus helpers they share.
"""

from datetime import datetime, timedelta

from mcmanager.database import permissions


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
    permission = permissions.PLAYER

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

    def allowed(self, db):
        """True if the player who triggered this event may run it."""
        if self.permission <= permissions.PLAYER:
            return True

        return permissions.check_permission(
            db, self.server.id, self.player, self.permission
        )

    def action(self, db):
        pass

    def get_details(self, db):
        """Return a string with details about the event, for logging."""
        return None

    @staticmethod
    def get_command():
        """Return the command that triggers this event, if any."""
        return None