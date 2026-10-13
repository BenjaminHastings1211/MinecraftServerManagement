#!/usr/bin/env python3
"""mc-confirm: accept the Minecraft EULA for servers."""

from resources import cli


EULA_URL = "https://aka.ms/MinecraftEULA"


def accept(server):
    if server.eula_approved():
        print(f"EULA already accepted for {cli.server_label(server)}.")
        return

    server.accept_eula()
    print(cli.green(f"EULA accepted for {cli.server_label(server)}."))


def main():
    parser = cli.parser(
        f"Accept the Minecraft EULA ({EULA_URL}) so servers can start.",
        target=cli.ALL,
    )
    args = parser.parse_args()

    print(f"By accepting you agree to the Minecraft EULA: {EULA_URL}\n")

    return cli.for_each(cli.resolve(args.server), accept)


if __name__ == "__main__":
    cli.run(main)
