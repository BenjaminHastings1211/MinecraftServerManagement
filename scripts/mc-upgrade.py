#!/usr/bin/env python3
"""mc-upgrade: move servers to a new Minecraft version."""

import _bootstrap

from functools import cache

from mcmanager import cli, versions


RESTART_WARNING_SECONDS = 30


def upgrade(server, version, get_jar, restart=True):
    print(cli.bold(cli.server_label(server)))

    current = server.version

    if current == version:
        print(f"  Already on {version}.\n")
        return

    if versions.version_key(version) < versions.version_key(current):
        raise cli.CommandError(
            f"{version} is older than the current {current}; "
            "Minecraft worlds can't be safely downgraded."
        )

    print(f"  {current} -> {version}")
    jar = get_jar()

    if server.world_path.is_dir():
        print("  Backing up world...", flush=True)
        path, paused = server.backup(label=f"pre-{version}")

        if not paused:
            cli.warning(f"{server.id}: saving couldn't be paused; backup may be inconsistent.")

        print(f"  Saved as {path.name}")

    server.update_version(jar, version)
    print(cli.green(f"  Updated to {version}."))

    if not server.is_running():
        print()
        return

    if not restart:
        print("  Restart the server to use the new version.\n")
        return

    print(f"  Restarting (players get {RESTART_WARNING_SECONDS}s warning)...", flush=True)
    seconds = server.restart(
        warn_seconds=RESTART_WARNING_SECONDS,
        reason=f"updating to {version}",
    )
    print(cli.green(f"  Ready in {cli.format_duration(seconds, precise=True)}\n"))


def main():
    parser = cli.parser(
        "Upgrade servers to a Minecraft version (default: latest "
        "release). The world is backed up first and running servers "
        "are restarted. 'all' only upgrades servers with auto_update on.",
        target=cli.ALL,
    )
    parser.add_argument(
        "-v", "--version",
        help="version to install, e.g. 26.3 (default: latest release)",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="don't restart running servers; the new version applies on next start",
    )
    args = parser.parse_args()

    servers = cli.resolve(args.server)

    if args.server.lower() == "all":
        servers = [s for s in servers if s.config.get("auto_update", False)]

        if not servers:
            print("No servers have auto_update enabled.")
            return

    version = args.version or versions.latest_release()
    print(f"Target version: {version}\n")

    # Only download once a server actually needs it.
    get_jar = cache(lambda: versions.download(version))

    return cli.for_each(
        servers,
        lambda server: upgrade(server, version, get_jar, not args.no_restart),
    )


if __name__ == "__main__":
    cli.run(main)
