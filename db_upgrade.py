#!/usr/bin/env python3
from scripts.resources.database.migrations import run
from scripts.resources.database.client import DatabaseClient

with DatabaseClient() as db:
    run(db)