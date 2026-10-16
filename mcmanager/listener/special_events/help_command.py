import re

from mcmanager.messages import tellraw
from mcmanager.database import permissions
from mcmanager.listener.base import Event


class HelpCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!help$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        from mcmanager.listener.events import EVENTS

        message = (
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" Commands", bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        level = permissions.get_level(db, self.server.id, self.player)

        for event_class in EVENTS:
            details = event_class.get_details()

            if details and permissions.is_allowed(level, event_class.permission):
                message.text("\n")
                message.text("- ", bold=True, color="#555555")
                message.text(event_class.get_command(), bold=True, color="#ff0000")
                message.text(": ", bold=True, color="#555555")
                message.text(details, color="#aaaaaa")

        self.server.notify(message)

    @staticmethod
    def get_details():
        return "Shows a list of available commands."

    @staticmethod
    def get_command():
        return "!help"