#!/usr/bin/env python3
import _bootstrap

from mcmanager import cli, tellraw

def main():
    parser = cli.parser("Restart the RCON listener for every running server.", target=None)
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="don't announce the restart in-game",
    )
    args = parser.parse_args()

    servers = cli.resolve("all")

    for server in servers:
        if not server.is_running():
            continue

        print("Rebooting RCON listener for %s."%server.name)

        server.stop_listener();
        server.ensure_listener();

        if not args.quiet:
            server.tell(
                tellraw.to_all()
                .text("Lutzcraft RCON", color="#00ff00")
                .text(": back online.")
            )


if __name__ == "__main__":
    cli.run(main)
