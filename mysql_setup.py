#!/usr/bin/env python3

"""Initialize the database using mcmanager/database/schema.sql."""

import scripts._bootstrap

import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "mcmanager" / "database" / "schema.sql"


def main():
    load_dotenv(ROOT / ".env")

    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "minecraft")

    if not user:
        sys.exit("Error: DB_USER is missing from .env")

    if not SCHEMA.is_file():
        sys.exit(f"Error: Schema file not found: {SCHEMA}")

    client = shutil.which("mariadb") or shutil.which("mysql")

    if not client:
        sys.exit("Error: MariaDB/MySQL client not found. Install mariadb-client.")

    env = os.environ.copy()
    env["MYSQL_PWD"] = password

    command = [
        client,
        "--host", host,
        "--port", port,
        "--user", user,
        "--default-character-set=utf8mb4",
        database,
    ]

    print(f"Initializing database '{database}'...")
    print(f"Loading schema from {SCHEMA}")

    try:
        with SCHEMA.open("r", encoding="utf-8") as schema_file:
            subprocess.run(
                command,
                stdin=schema_file,
                env=env,
                check=True,
            )
    except subprocess.CalledProcessError as error:
        sys.exit(f"Database setup failed (exit code {error.returncode}).")
    except OSError as error:
        sys.exit(f"Could not run database setup: {error}")

    print("Database setup complete.")

if __name__ == "__main__":
    main()