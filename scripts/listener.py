#!/usr/bin/env python3
"""
mc-listen: follow a server's log and run an action for each event
(see resources/events.py).

mc-start launches this in the background for every server and mc-stop
ends it. Run it by hand to watch what it does; stop it with Ctrl-C.
"""

import time
import traceback

from resources import cli, events
from resources.console import LogFollower, LogLine
from resources import tellraw


POLL_INTERVAL = 0.25


def listen(server):
    follower = LogFollower(server.path / "logs" / "latest.log")
    follower.read()  # Start from the current end; don't replay old lines.

    print(f"Listening to {cli.server_label(server)}.", flush=True)

    try:
        with server.db as db:
            while True:
                for raw in follower.read():
                    try:
                        event = events.classify(
                            server,
                            LogLine.parse(raw),
                            db,
                        )

                        if event is None:
                            continue

                        print(event, flush=True)
                        event.action(db)

                    except Exception as e:
                        print(f"Error processing log line: {e}", flush=True)
                        traceback.print_exc()

                        try:
                            server.tell(
                                tellraw.to_all()
                                .text("Error: ", bold=True, color="#ff5555")
                                .text(str(e))
                            )
                        except Exception:
                            traceback.print_exc()

                time.sleep(POLL_INTERVAL)
    finally:
        follower.close()


def main():
    parser = cli.parser("Run a server's event listener.", target=cli.ONE)
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)
    listen(server)


if __name__ == "__main__":
    cli.run(main)
