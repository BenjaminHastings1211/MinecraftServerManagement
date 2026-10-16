#!/usr/bin/env python3
import _bootstrap

from mcmanager import cli, tellraw

def main():
    parser = cli.parser(
        "Restart the RCON listener for every running server, or just one.",
        target=None,
    )
    parser.add_argument(
        "-s", "--server",
        default="all",
        help="server ID, e.g. 2 (or server-002); default: all running servers",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="don't announce the restart in-game",
    )
    args = parser.parse_args()

    servers = cli.resolve(args.server)
    one_server = args.server.strip().lower() != "all"

    for server in servers:
        if not server.is_running():
            if one_server:
                raise cli.CommandError(f"{cli.server_label(server)} is not running.")

            continue

        print("Rebooting RCON listener for %s."%server.name)

        server.stop_listener();
        server.ensure_listener();

        if not args.quiet:
            server.notify(
                tellraw.to_all()
                .text("Lutzcraft RCON", color="#00ff00")
                .text(": back online.")
            )


if __name__ == "__main__":
    cli.run(main)
