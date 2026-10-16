import re

from mcmanager.listener.base import Event
from mcmanager.messages import tellraw
from mcmanager.database import permissions


class PlayerOp(Event):
    pattern = re.compile(
        r"^(?:System chat: )?\[(?P<actor>[^:]+): Made (?P<target>\S+) a server operator\]$"
    )

    @property
    def actor(self):
        return self.match["actor"]

    @property
    def target(self):
        return self.match["target"]

    def action(self, db):
        try:
            permissions.set_role(db, self.server.id, self.target, permissions.OP)
        except ValueError:
            self.server.notify(
                tellraw.to_player(self.actor)
                .text(self.target)
                .text(" does not exist on ")
                .text(self.server.name, bold=True, color="aqua")
                .text(" yet.")
            )

class PlayerDeOp(Event):
    pattern = re.compile(
        r"^(?:System chat: )?\[(?P<actor>[^:]+): Made (?P<target>\S+) no longer a server operator\]$"
    )

    @property
    def actor(self):
        return self.match["actor"]

    @property
    def target(self):
        return self.match["target"]

    def action(self, db):
        try:
            permissions.set_role(db, self.server.id, self.target, permissions.PLAYER)
        except ValueError:
            self.server.notify(
                tellraw.to_player(self.actor)
                .text(self.target)
                .text(" does not exist on ")
                .text(self.server.name, bold=True, color="aqua")
                .text(" yet.")
            )