#!/usr/bin/env python3
"""mc-stop: cleanly stop running servers."""

import _bootstrap  # noqa: F401  (must come first; see _bootstrap.py)

from mcmanager import cli


def stop(server, timeout):
    process = server.get_process()

    if process is None:
        if server.get_listener() is not None:
            server.stop()
            print(f"{cli.server_label(server)} is not running. Stopped its listener.")
        else:
            print(f"{cli.server_label(server)} is not running.")
        return

    print(f"Stopping {cli.server_label(server)} (PID {process.pid})...", flush=True)

    if not server.stop(timeout=timeout):
        raise cli.CommandError(
            f"did not stop within {timeout} seconds. "
            "Left running to avoid an unsafe shutdown."
        )

    print(cli.green("  Stopped."))


def main():
    parser = cli.parser("Cleanly stop Minecraft servers.", target=cli.ALL)
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=60,
        help="seconds to wait for a clean shutdown (default: 60)",
    )
    args = parser.parse_args()

    servers = cli.resolve(args.server)

    if args.server.lower() == "all":
        servers = [s for s in servers if s.is_running() or s.get_listener()]
        print(f"Stopping {len(servers)} running server(s)...\n")

    return cli.for_each(servers, lambda server: stop(server, args.timeout))


if __name__ == "__main__":
    cli.run(main)
