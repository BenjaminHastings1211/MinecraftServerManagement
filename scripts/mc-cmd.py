#!/usr/bin/env python3
"""mc-cmd: send commands to running servers and watch their live output."""

import _bootstrap  # noqa: F401  (must come first; see _bootstrap.py)

import threading
import time

from collections import deque

from mcmanager import cli
from mcmanager.console import LogFollower, LogLine


HISTORY_LINES = 10


def show(line):
    if line.level == "WARN":
        print(cli.orange(line.raw))
    elif line.level in ("ERROR", "FATAL"):
        print(cli.red(line.raw))
    elif line.chat or line.joined or line.left:
        print(cli.bold(line.raw))
    else:
        print(line.raw)


def recent_lines(server, count=HISTORY_LINES):
    log = server.path / "logs" / "latest.log"

    if not log.is_file():
        return []

    with log.open("r", encoding="utf-8", errors="replace") as file:
        return [LogLine.parse(line) for line in deque(file, maxlen=count)]


def follow(server):
    """Print the server's output as it happens, until Ctrl-C."""
    print(f"Following {cli.server_label(server)}. Press Ctrl-C to stop.\n")

    for line in recent_lines(server):
        show(line)

    follower = LogFollower(server.path / "logs" / "latest.log")
    follower.read()

    try:
        while True:
            for raw in follower.read():
                show(LogLine.parse(raw))

            time.sleep(0.25)
    except KeyboardInterrupt:
        print()
    finally:
        follower.close()


def interactive(server):
    """A console prompt with the server's live output scrolling above it."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout

    session = PromptSession(history=FileHistory(str(server.path / ".command_history")))
    stop = threading.Event()

    with server.console() as console, patch_stdout(raw=True):
        print(
            f"Connected to {cli.server_label(server)}. "
            "Type 'exit' or press Ctrl-D to leave.\n"
        )

        for line in recent_lines(server):
            show(line)

        def print_output():
            for line in console.lines(stop):
                show(line)

        threading.Thread(target=print_output, daemon=True).start()

        try:
            while True:
                try:
                    command = session.prompt(f"{server.name}> ").strip()
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break

                if command in ("exit", "quit"):
                    break

                if command:
                    reply = console.command(command)

                    if reply:
                        print(cli.green(reply))
        finally:
            stop.set()


def main():
    parser = cli.parser(
        "Send a command to a running server and print its reply. With "
        "no command, opens an interactive console showing live output.",
        target=cli.ALL,
    )
    parser.add_argument(
        "-f", "--follow",
        action="store_true",
        help="just watch the server's live output",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="command to run, e.g. 'say hello' or 'list' (leading / optional)",
    )
    args = parser.parse_args()

    command = " ".join(args.command).strip()
    servers = cli.resolve(args.server)

    if args.server.lower() == "all":
        if not command or args.follow:
            parser.error("with all, give a command (and no --follow).")

        def send_labelled(server):
            print(cli.bold(f"[{server.name}]"))
            print(server.command(command) or "(no reply)")

        return cli.for_each([s for s in servers if s.is_running()], send_labelled)

    (server,) = servers

    if args.follow:
        follow(server)
    elif command:
        reply = server.command(command)

        if reply:
            print(reply)
    else:
        interactive(server)


if __name__ == "__main__":
    cli.run(main)
