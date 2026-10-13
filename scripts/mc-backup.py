#!/usr/bin/env python3
"""mc-backup: back up worlds (pausing saves on running servers) and list backups."""

from resources import cli


def backup(server, force):
    print(cli.bold(cli.server_label(server)))

    if not (force or server.config.get("backup_enabled", False)):
        print("  Backups disabled, skipping (use --force to back up anyway).")
    else:
        path, paused = server.backup()

        if not paused:
            cli.warning(
                f"{server.id}: couldn't pause saving over RCON, so the "
                "backup may be inconsistent. Restart the server to enable RCON."
            )

        print(f"  Created {path.name} ({cli.format_bytes(path.stat().st_size)})")

    server.update_size()
    print(f"  Size: server {server.config['size']:.1f} GB, backups {server.config['backup_size']:.1f} GB\n")


def main():
    parser = cli.parser(
        "Back up server worlds. Running servers keep running; saving "
        "is paused during the backup. Old backups beyond "
        "backup_history_size are removed.",
        target=cli.ALL,
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="back up even if backup_enabled is false",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="list existing backups instead of making one",
    )
    args = parser.parse_args()

    servers = cli.resolve(args.server)

    if args.list:
        return cli.for_each(servers, cli.print_backups)

    return cli.for_each(servers, lambda server: backup(server, args.force))


if __name__ == "__main__":
    cli.run(main)
