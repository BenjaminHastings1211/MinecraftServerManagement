#!/usr/bin/env python3
import scripts._bootstrap  # noqa: F401  (must come first; see scripts/_bootstrap.py)

from mcmanager.database.migrations import run
from mcmanager.database.client import DatabaseClient

with DatabaseClient() as db:
    run(db)
