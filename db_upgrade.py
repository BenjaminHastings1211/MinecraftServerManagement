#!/usr/bin/env python3
"""Run pending SQL migrations (see mcmanager/database/migrations/migrate.py)."""

import scripts._bootstrap

import argparse

from mcmanager.database.client import DatabaseClient
from mcmanager.database.migrations import migrate


def main():
    parser = argparse.ArgumentParser(description="Run pending SQL migrations.")
    args = parser.parse_args()

    with DatabaseClient() as db:
        migrate.run(db)


if __name__ == "__main__":
    main()
