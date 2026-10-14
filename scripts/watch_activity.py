#!/usr/bin/env python3
"""mc-watch: print every line of a running server's activity, fully parsed."""

import _bootstrap

from mcmanager import cli


def main():
    parser = cli.parser("Print a running server's activity as it happens.", target=cli.ONE)
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)

    with server.console() as console:
        print(f"Watching {cli.server_label(server)}: {console.command('list')}")
        print("Press Ctrl-C to stop.\n")

        for line in console.lines():
            print({
                "time": line.time,
                "source": line.source,
                "level": line.level,
                "message": line.message,
            })


if __name__ == "__main__":
    cli.run(main)
