import re

from mcmanager.listener.base import Event
from mcmanager.database import players


class ServerBoot(Event):
    pattern = re.compile(r'^Done \(\d+\.\d+s\)! For help, type "help"$')

    def action(self, db):
        has_init = db.query(
            "SELECT has_init FROM servers WHERE id = %s",
            [self.server.id]
        ).first()['has_init']

        if not has_init:
            db.query(
                "UPDATE servers SET has_init = TRUE WHERE id = %s",
                [self.server.id]
            )

            self.server.initialize()

