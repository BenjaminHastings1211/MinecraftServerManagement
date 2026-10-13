#!/usr/bin/env python3
"""mc-restore: replace a server's world with one of its backups."""

import _bootstrap  # noqa: F401  (must come first; see _bootstrap.py)

import time

from mcmanager import cli


def choose_backup(server, choice):
    backups = server.backups()

    if not backups:
        raise cli.CommandError(f"{cli.server_label(server)} has no backups.")

    if choice is None:
        cli.print_backups(server)
        choice = input("Restore which backup? (number): ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(backups):
        return backups[int(choice) - 1]

    for path in backups:
        if path.name == choice:
            return path

    raise cli.CommandError(f"No such backup: {choice}")


def main():
    parser = cli.parser(
        "Restore a server's world from a backup. The current world is "
        "backed up first, and a running server is stopped and restarted.",
        target=cli.ONE,
    )
    parser.add_argument(
        "backup",
        nargs="?",
        help="backup number (as shown by mc-backup --list) or file name; "
             "asks if omitted",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="don't ask for confirmation",
    )
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)
    backup = choose_backup(server, args.backup)
    was_running = server.is_running()

    print()
    print(f"Restore {cli.server_label(server)} to {backup.name}?")

    if was_running:
        print("The server will be stopped and started again.")

    if not args.yes and not cli.confirm("Continue?"):
        print("Restore cancelled.")
        return

    if was_running:
        if server.announce("Server restoring a backup in 10 seconds."):
            time.sleep(10)

        print("Stopping server...", flush=True)

        if not server.stop():
            raise cli.CommandError("Server did not stop; restore cancelled.")

    print("Backing up the current world first...", flush=True)
    safety, _ = server.backup(label="pre-restore", prune=False)
    print(f"  Saved as {safety.name}")

    print(f"Restoring {backup.name}...", flush=True)
    server.restore(backup)
    print(cli.green("  World restored."))

    if was_running:
        print("Starting server...", flush=True)
        seconds = server.wait_until_ready(server.start(background=True))
        print(cli.green(f"  Ready in {cli.format_duration(seconds, precise=True)}"))


if __name__ == "__main__":
    cli.run(main)
