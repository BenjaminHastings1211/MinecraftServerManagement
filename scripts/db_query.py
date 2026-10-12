#!/usr/bin/env python3
"""mc-db: run SQL against the 'minecraft' database and show the results."""

import json
import sys

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from resources import cli
from resources.database import Database, DatabaseError


HISTORY_FILE = Path.home() / ".mc_db_history"
MAX_CELL_WIDTH = 60


# Output

def cell(value):
    if value is None:
        return "NULL"

    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"

    text = str(value).replace("\n", "\\n")

    if len(text) > MAX_CELL_WIDTH:
        text = text[:MAX_CELL_WIDTH - 1] + "…"

    return text


def print_table(result):
    if not result.columns:
        message = f"OK, {result.rowcount} row(s) affected"

        if result.lastrowid:
            message += f", last insert id {result.lastrowid}"

        print(cli.green(message + "."))
        return

    table = [[cell(row[column]) for column in result.columns] for row in result.rows]
    widths = [
        max([len(column)] + [len(line[index]) for line in table])
        for index, column in enumerate(result.columns)
    ]

    def line(values):
        return "  ".join(value.ljust(width) for value, width in zip(values, widths))

    print(cli.bold(line(result.columns)))
    print("  ".join("─" * width for width in widths))

    for values in table:
        print(line(values))

    print(f"\n{len(result.rows)} row(s).")


def json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, timedelta):
        return value.total_seconds()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    raise TypeError(f"Cannot convert {type(value).__name__} to JSON")


def print_json(result):
    print(json.dumps(
        {
            "columns": result.columns,
            "rows": result.rows,
            "rowcount": result.rowcount,
            "lastrowid": result.lastrowid,
        },
        default=json_value,
        indent=2,
    ))


# Running

def run_one(db, sql, as_json):
    result = db.query(sql)

    if as_json:
        print_json(result)
    else:
        print_table(result)


def interactive(db, as_json):
    """A SQL prompt; statements end with ';'."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    session = PromptSession(history=FileHistory(str(HISTORY_FILE)))

    print(
        f"Connected to '{db.database}' as {db.user}. End statements with ';'. "
        "Type 'exit' or press Ctrl-D to leave.\n"
    )

    buffer = []

    while True:
        try:
            text = session.prompt("sql> " if not buffer else "  -> ")
        except KeyboardInterrupt:
            buffer = []
            continue
        except EOFError:
            print()
            return

        if not buffer and text.strip().lower() in ("exit", "quit", r"\q"):
            return

        buffer.append(text)
        sql = "\n".join(buffer).strip()

        if not sql:
            buffer = []
        elif sql.endswith(";"):
            buffer = []

            try:
                run_one(db, sql.rstrip(";"), as_json)
            except DatabaseError as error:
                cli.error_line(error)

            print()


def main():
    parser = cli.parser(
        "Run SQL against the minecraft database. With no SQL, opens an "
        "interactive prompt.",
        target=None,
    )
    parser.add_argument(
        "sql",
        nargs="?",
        help="statement to run, or '-' to read it from stdin",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print results as JSON",
    )
    args = parser.parse_args()

    with Database() as db:
        if args.sql is None:
            interactive(db, args.json)
            return 0

        sql = sys.stdin.read() if args.sql == "-" else args.sql

        try:
            run_one(db, sql.strip().rstrip(";"), args.json)
        except DatabaseError as error:
            raise cli.CommandError(error) from None

    return 0


if __name__ == "__main__":
    cli.run(main)
