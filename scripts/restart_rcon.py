from resources import cli, tellraw

def main():
    parser = cli.parser(
        "For a running server, reboot the RCON listender",
        target=cli.ONE,
    )

    args = parser.parse_args()

    server = cli.resolve(args.server)[0]

    if not server.is_running():
        print(server, "is not running.")
        return 1

    print("Stopping RCON Listner...");
    server.stop_listener();
    print("Starting RCON Listner...");
    server.ensure_listener();

    server.tell(
        tellraw.to_all()
        .text("Lutzcraft RCON", color="#00ff00")
        .text(": back online.")
    )


if __name__ == "__main__":
    cli.run(main)
