#!/usr/bin/env python3
"""mc-reinit: mark players for reinitialization on their next join."""

import _bootstrap

from mcmanager import cli
from mcmanager.database import servers


def reinit(server):
    with server.db as db:
        try:
            servers.set_players_reinit_after(db, server.id)
            print(f"Players on {cli.server_label(server)} will be reinitialized.")
        finally:
            db.close()


def main():
    parser = cli.parser(
        description="Mark players for reinitialization.",
        target=cli.ALL,
    )
    args = parser.parse_args()

    selected_servers = cli.resolve(args.server)

    return cli.for_each(selected_servers, reinit)


if __name__ == "__main__":
    cli.run(main)