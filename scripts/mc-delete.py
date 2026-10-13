#!/usr/bin/env python3
"""mc-delete: mark a server inactive, hiding it from every script."""

from resources import cli


def main():
    parser = cli.parser(
        "Mark a server inactive. It disappears from every script; its "
        "folder, world and backups are left on disk.",
        target=cli.ONE,
    )
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)

    if server.is_running():
        raise cli.CommandError(
            f"{cli.server_label(server)} is running. "
            f"Stop it first with: mc-stop {cli.short_id(server)}"
        )

    cli.heading("Delete Minecraft Server")

    print(f"Server:       {server.name}")
    print(f"ID:           {server.id}")
    print(f"Version:      {server.version}")
    print(f"Created:      {cli.format_date(server.created)}")
    print(f"Age:          {cli.format_age(server.created)}")
    print(f"Backups:      {len(server.backups())}")
    print(f"Location:     {server.path}")
    print()
    print(cli.orange("This marks the server inactive. It will no longer"))
    print(cli.orange("appear in any script, but its folder stays on disk."))
    print()

    if not cli.confirm(f"Delete '{server.name}'?"):
        print("Deletion cancelled.")
        return

    server.delete()
    print(cli.green(f"{server.name} marked inactive. Files kept at {server.path}"))


if __name__ == "__main__":
    cli.run(main)
