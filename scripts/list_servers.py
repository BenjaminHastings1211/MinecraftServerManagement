#!/usr/bin/env python3
"""mc-list: overview of all servers, or details of one."""

from resources import cli
from resources.server import Server


def status(server, process):
    """(dot, word) describing whether the server is up."""
    if process is not None:
        return cli.green("●"), cli.green("Running")

    if not server.eula_approved():
        return cli.orange("●"), cli.orange("EULA required")

    return cli.red("●"), cli.red("Stopped")


def format_players(players):
    if players is None:
        return "players unknown"

    online, maximum, names = players
    text = f"{online}/{maximum} players"

    return f"{text}: {', '.join(names)}" if names else text


def backups_text(server):
    if not server.config.get("backup_enabled", False):
        return "Backups no"

    return f"Backups {float(server.config.get('backup_size', 0)):.1f} GB"


def print_overview(servers):
    cli.heading("Minecraft Servers", width=78)

    for server in servers:
        process = server.get_process()
        dot, _ = status(server, process)
        on_boot = cli.yes_no(server.config.get("on_boot", False))
        size = float(server.config.get("size", 0))
        indent = " " * 18

        print(f"{dot} {server.name:<15} {server.id}")
        print(f"{indent}{server.version}  •  {cli.format_age(server.created)}  •  {size:.1f} GB")

        if process is None:
            print(f"{indent}Port {server.port}  •  Boot {on_boot}  •  {backups_text(server)}")
        else:
            uptime = cli.format_duration(server.uptime())
            print(
                f"{indent}Port {server.port}  •  PID {process.pid}  •  Up {uptime}  •  "
                f"Boot {on_boot}  •  {backups_text(server)}"
            )
            print(f"{indent}{format_players(server.players())}")

        print()


def print_details(server):
    config = server.config
    process = server.get_process()
    _, word = status(server, process)
    backups_enabled = config.get("backup_enabled", False)

    cli.heading("Minecraft Server")

    print(f"Name:             {server.name}")
    print(f"ID:               {server.id}")
    print(f"Status:           {word}")

    if process is not None:
        print(f"PID:              {process.pid}")
        print(f"Uptime:           {cli.format_duration(server.uptime())}")
        print(f"Players:          {format_players(server.players())}")

    if config.get("description"):
        print(f"Description:      {config['description']}")

    print(f"Version:          {server.version}")
    print(f"Created:          {cli.format_date(server.created)}")
    print(f"Age:              {cli.format_age(server.created)}")
    print(f"Port:             {server.port}")
    print()
    print("RAM:")
    print(f"  Minimum:        {config.get('ram_min', '?')}")
    print(f"  Maximum:        {config.get('ram_max', '?')}")
    print()
    print(f"Boot on startup:  {cli.yes_no(config.get('on_boot', False))}")
    print(f"Auto-update:      {cli.yes_no(config.get('auto_update', False))}")
    print(f"EULA:             {cli.yes_no(server.eula_approved())}")
    print()
    print("Storage:")
    print(f"  Server:         {float(config.get('size', 0)):.1f} GB")
    print(f"  Backups:        {float(config.get('backup_size', 0)):.1f} GB")
    print()
    print("Backups:")
    print(f"  Enabled:        {cli.yes_no(backups_enabled)}")

    if backups_enabled:
        print(f"  History:        {config.get('backup_history_size', '?')}")

    print(f"  Stored:         {len(server.backups())}")
    print()
    print(f"Location:         {server.path}")
    print()


def main():
    parser = cli.parser("List all servers, or show details of one.", target=None)
    parser.add_argument(
        "server",
        nargs="?",
        help="server ID to show in detail, e.g. 2 for server-002",
    )
    args = parser.parse_args()

    if args.server is None:
        servers = Server.all()

        if not servers:
            print("No Minecraft servers found.")
            return

        print_overview(servers)
        return

    (server,) = cli.resolve(args.server)
    print_details(server)


if __name__ == "__main__":
    cli.run(main)
