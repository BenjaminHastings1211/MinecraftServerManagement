#!/usr/bin/env python3
import _bootstrap

from mcmanager import cli, tellraw

def main():
    servers = cli.resolve("all")

    for server in servers:
        if not server.is_running():
            continue

        print("Rebooting RCON listener for %s."%server.name)

        server.stop_listener();
        server.ensure_listener();

        server.tell(
            tellraw.to_all()
            .text("Lutzcraft RCON", color="#00ff00")
            .text(": back online.")
        )


if __name__ == "__main__":
    cli.run(main)
