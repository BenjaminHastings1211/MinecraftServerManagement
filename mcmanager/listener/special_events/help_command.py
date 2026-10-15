import re

from mcmanager import tellraw
from mcmanager.listener.base import Event


class HelpCommand(Event):
    pattern = re.compile(r"^(?:\[Not Secure\] )?<(?P<player>[^>]+)> \!help$")

    @property
    def player(self):
        return self.match["player"]

    def action(self, db):
        from mcmanager.listener.events import EVENTS
        self.server.tell(
            tellraw.to_player(self.player)
            .text("━━━ ", color="#555555")
            .text(self.server.name, bold=True, color="#00ff00")
            .text(" ━━━", color="#555555")
        )

        for event_class in EVENTS:
            details = event_class.get_details()
            if details:
                self.server.tell(
                    tellraw.to_player(self.player)
                    .text(details, color="#aaaaaa")
                )

    def get_details(self):
        return "!help - Shows a list of available commands."
    