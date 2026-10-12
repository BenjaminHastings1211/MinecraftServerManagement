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
        while True:
            for raw in follower.read():
                event = events.classify(server, LogLine.parse(raw))

                if event is None:
                    continue

                print(event, flush=True)

                # One bad event mustn't stop the listener.
                try:
                    event.action()
                except Exception as e:
                    server.tell(
                        tellraw.to_all()
                        .text("Error: ", bold=True, color="#ff5555")
                        .text(str(e))
                    )
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
