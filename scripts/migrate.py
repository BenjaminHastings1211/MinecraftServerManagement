from resources.database.migrations import run
from resources.database.client import DatabaseClient

with DatabaseClient() as db:
    run(db)