#!/usr/bin/env python3
"""Run pending SQL migrations (see mcmanager/database/migrations/migrate.py)."""

import scripts._bootstrap

import argparse

from mcmanager.database.client import DatabaseClient
from mcmanager.database.migrations import migrate


def main():
    parser = argparse.ArgumentParser(description="Run pending SQL migrations.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would run without changing the database",
    )
    args = parser.parse_args()

    with DatabaseClient() as db:
        migrate.run(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
