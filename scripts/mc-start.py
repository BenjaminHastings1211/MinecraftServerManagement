#!/usr/bin/env python3
"""mc-start: start servers in the background (or attached with --console)."""

import _bootstrap

import argparse

from mcmanager import cli


def start(server, console=False, wait=True):
    if server.is_running():
        print(f"{cli.server_label(server)} is already running.")

        if server.get_listener() is None:
            server.ensure_listener()
            print("  Started its listener.")

        return

    for key in server.unknown_properties():
        cli.warning(
            f"{server.folder}: '{key}' is not a server.properties key "
            "and will be ignored."
        )

    print(f"Starting {cli.server_label(server)}...", flush=True)
    process = server.start(background=not console)
    print(f"  PID {process.pid}", flush=True)

    if console:
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\nConsole interrupted. Waiting for the server to exit...")
            process.wait()
        finally:
            # The server has exited: stop its listener, log players out.
            server.stop()
        return

    if wait:
        seconds = server.wait_until_ready(process)
        print(cli.green(f"  Ready in {cli.format_duration(seconds, precise=True)}"))


def main():
    parser = cli.parser(
        "Start Minecraft servers in the background. "
        "'all' starts every server with on_boot enabled.",
        target=cli.ALL,
    )
    parser.add_argument(
        "-c", "--console",
        action="store_true",
        help="run attached to this terminal instead (single server only)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="return without waiting for the server to finish loading",
    )
    # Background is the default now; -b is still accepted so old
    # habits keep working.
    parser.add_argument("-b", "--background", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    servers = cli.resolve(args.server)

    if args.server.lower() == "all":
        if args.console:
            parser.error("--console cannot be used with all.")

        servers = [s for s in servers if s.config.get("on_boot", False)]
        print(f"Starting {len(servers)} boot-enabled server(s)...\n")

    return cli.for_each(
        servers,
        lambda server: start(server, args.console, not args.no_wait),
    )


if __name__ == "__main__":
    cli.run(main)
