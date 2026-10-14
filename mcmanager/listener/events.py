"""
To handle a new kind of message, add a file to special_events/ with a
subclass of base.Event that has a `pattern` (a regex matched against
LogLine.message) and an action(), then add it to EVENTS. Named groups
in the pattern are available as event.match["name"].
"""

from mcmanager.listener.special_events.chat import Chat
from mcmanager.listener.special_events.death import Death
from mcmanager.listener.special_events.death_location_command import DeathLocationCommand
from mcmanager.listener.special_events.login import Login
from mcmanager.listener.special_events.logout import Logout
from mcmanager.listener.special_events.playtime_command import PlaytimeCommand


# The order of parcing matters so check this
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
