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
from mcmanager.listener.special_events.help_command import HelpCommand
from mcmanager.listener.special_events.find_command import FindCommand
from mcmanager.listener.special_events.operator_updates import PlayerOp, PlayerDeOp
from mcmanager.listener.special_events.server_boot import ServerBoot
from mcmanager.listener.special_events.perm_level_command import PermCommand


# The order of parcing matters so check this
EVENTS = [
    ServerBoot,
    Login,
    Logout,
    PlayerOp,
    PlayerDeOp,
    Death,
    DeathLocationCommand,
    PlaytimeCommand,
    PermCommand,
    HelpCommand,
    FindCommand,
    Chat,
]


def classify(server, line, db):
    """Return the first event that matches the line, or None."""
    for event_class in EVENTS:
        event = event_class.parse(server, line, db)

        if event is not None:
            return event

    return None
