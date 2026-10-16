#!/usr/bin/env python3
"""mc-create: create a new server from defaults.json."""

import _bootstrap

from mcmanager import cli, versions
from mcmanager.server import Server


def main():
    parser = cli.parser("Create a new Minecraft server.", target=None)
    parser.add_argument("name", help="name of the new server")
    parser.add_argument(
        "-v", "--version",
        help="version number (downloaded from Mojang if needed) or JAR "
             "filename in versions/ (default: newest local version)",
    )
    args = parser.parse_args()

    if args.version and not args.version.endswith(".jar"):
        print(f"Getting Minecraft {args.version}...", flush=True)
        versions.download(args.version)

    print(f"Creating {args.name}...", flush=True)
    server = Server.create(args.name, args.version)

    print(cli.green(f"Created {cli.server_label(server)}"))
    print(f"  Version:  {server.version}")
    print(f"  Port:     {server.port}")
    print(f"  Location: {server.path}")
    print()
    print("Next steps:")
    print(f"  mc-confirm {server.id}   accept the Minecraft EULA")
    print(f"  mc-start {server.id}     start it")


if __name__ == "__main__":
    cli.run(main)
