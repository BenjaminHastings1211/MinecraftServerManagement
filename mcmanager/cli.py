"""
Shared command-line plumbing for the mc-* scripts.

Every script follows the same shape:

    from mcmanager import cli

    def main():
        parser = cli.parser("Do something.", target=cli.ALL)
        args = parser.parse_args()
        return cli.for_each(cli.resolve(args.server), do_something)

    if __name__ == "__main__":
        cli.run(main)
"""

import argparse
import sys

from datetime import datetime

import psutil

from mcmanager.server import Server


ONE = "one"
ALL = "all"

# Errors that are reported as a one-line "ERROR: ..." instead of a traceback.
EXPECTED_ERRORS = (OSError, ValueError, KeyError, RuntimeError, psutil.Error)


class CommandError(Exception):
    """A user-facing failure; the message is printed and the script exits 1."""


# Arguments

def parser(description, target=ONE):
    """
    An ArgumentParser with the standard server argument.

    target=ONE  adds  <server-id>
    target=ALL  adds  <server-id|all>
    target=None adds  nothing
    """
    parser = argparse.ArgumentParser(description=description)

    if target == ONE:
        parser.add_argument(
            "server",
            help="server ID, e.g. 2 (or its folder name, server-002)",
        )
    elif target == ALL:
        parser.add_argument(
            "server",
            help="server ID, e.g. 2 (or its folder name, server-002), or 'all'",
        )

    return parser


def resolve(value):
    """Turn a server argument into a list of Servers ('all' = every server)."""
    if value.strip().lower() == "all":
        servers = Server.all()

        if not servers:
            raise CommandError("No Minecraft servers found.")

        return servers

    return [Server(value)]


# Running

def run(main):
    """
    Run a script's main() with standard error handling, then exit
    with its return code (None counts as success).
    """
    try:
        code = main()
    except CommandError as error:
        error_line(error)
        code = 1
    except EXPECTED_ERRORS as error:
        error_line(error)
        code = 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        code = 130

    sys.exit(code or 0)


def for_each(servers, action):
    """
    Call action(server) for every server. A failure on one server is
    reported and the rest still run. Returns 1 if any failed (or
    returned False), otherwise 0.
    """
    failed = False

    for server in servers:
        try:
            if action(server) is False:
                failed = True
        except (CommandError, *EXPECTED_ERRORS) as error:
            error_line(f"{server.folder}: {error}")
            failed = True

    return 1 if failed else 0


def confirm(question):
    """Ask a yes/no question; only 'y' or 'yes' counts as yes."""
    return input(f"{question} (yes/no): ").strip().lower() in ("y", "yes")


# Output

_COLOUR = sys.stdout.isatty()


def _paint(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text


def green(text):
    return _paint("32", text)


def orange(text):
    return _paint("93", text)


def red(text):
    return _paint("31", text)


def bold(text):
    return _paint("1", text)


def error_line(message):
    sys.stdout.flush()
    print(f"ERROR: {message}", file=sys.stderr)


def warning(message):
    sys.stdout.flush()
    print(orange(f"WARNING: {message}"), file=sys.stderr)


def heading(title, width=40):
    print()
    print(bold(title))
    print("─" * width)
    print()


def server_label(server):
    return f"{server.name} ({server.folder})"


def print_backups(server):
    """Numbered list of a server's backups, newest first."""
    backups = server.backups()

    print(bold(server_label(server)))

    if not backups:
        print("  No backups.\n")
        return

    for number, path in enumerate(backups, 1):
        stat = path.stat()
        made = datetime.fromtimestamp(stat.st_mtime).strftime("%-d %b %Y %H:%M")
        print(f"  {number:>2}. {made:<18} {format_bytes(stat.st_size):>9}  {path.name}")

    print()


# Formatting

def yes_no(value):
    return "yes" if value else "no"


def format_duration(seconds, precise=False):
    """
    90061 -> '1d 1h 1m', or '1d 1h 1m 1s' with precise=True.
    Zero-valued leading units are dropped.
    """
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = [
        f"{value}{unit}"
        for value, unit in ((days, "d"), (hours, "h"), (minutes, "m"))
        if value
    ]

    if precise:
        parts.append(f"{seconds}s")
    elif not parts:
        parts.append("0m")

    return " ".join(parts)


def format_bytes(value):
    value = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"

        value /= 1024


def format_date(moment):
    return moment.strftime("%-d %b %Y") if moment else "Unknown"


def format_age(moment):
    if moment is None:
        return "Unknown"

    now = datetime.now(moment.tzinfo) if moment.tzinfo else datetime.now()
    days = (now - moment).days

    return f"{days} day" if days == 1 else f"{days} days"
