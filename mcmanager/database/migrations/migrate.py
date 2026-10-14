"""
SQL migration runner. Run it with ./db_upgrade.py.

Each *.sql file in this folder is one migration, run once in filename
order and tracked by filename in schema_migrations:

    pending -> running -> success
                       -> failed (error saved, exception re-raised)

Only successful migrations are skipped; pending, running (the runner
died mid-way) and failed ones are tried again on the next run.

Writing a migration:
  - One SQL statement per file.
  - MariaDB commits DDL (ALTER, CREATE, DROP) immediately; it cannot be
    rolled back, so a failure can leave a change half done. Retrying is
    only safe if the statement is idempotent. Prefer IF [NOT] EXISTS
    (e.g. ADD COLUMN IF NOT EXISTS). If that isn't possible, put the
    manual recovery steps in a comment at the top of the file.
  - Never edit a migration after it has run anywhere; add a new one.
"""

from pathlib import Path


def ensure_table(db):
    db.query(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INT UNSIGNED NOT NULL AUTO_INCREMENT,
            filename VARCHAR(255) NOT NULL,
            status ENUM('pending', 'running', 'success', 'failed')
                NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME NULL,
            executed_at DATETIME NULL,
            error_message TEXT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_migration_filename (filename)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )


def run(db):
    """
    Run pending SQL migrations in filename order.

    Migrations with pending, running, or failed status are retried.
    Successful migrations are skipped.

    Args:
        db: An open DatabaseClient connection.

    Returns:
        Number of migrations successfully executed.
    """
    migrations_dir = Path(__file__).resolve().parent

    ensure_table(db)

    applied = {
        row["filename"]: row["status"]
        for row in db.query(
            "SELECT filename, status FROM schema_migrations"
        ).rows
    }

    executed = 0

    for path in sorted(migrations_dir.glob("*.sql")):
        filename = path.name

        if applied.get(filename) == "success":
            print(f"[SKIP] {filename}")
            continue

        sql = path.read_text(encoding="utf-8").strip()

        if not sql:
            print(f"[SKIP] {filename}: empty file")
            continue

        if ";" in sql.rstrip(";"):
            raise ValueError(
                f"{filename} appears to contain multiple SQL statements. "
                "Use one statement per migration file."
            )

        # Record the migration before attempting its SQL.
        db.query(
            """
            INSERT INTO schema_migrations (filename, status)
            VALUES (%s, 'pending')
            ON DUPLICATE KEY UPDATE id = id
            """,
            [filename],
        )

        db.query(
            """
            UPDATE schema_migrations
            SET status = 'running',
                started_at = NOW(),
                executed_at = NULL,
                error_message = NULL
            WHERE filename = %s
            """,
            [filename],
        )

        print(f"[RUN] {filename}")

        try:
            db.query(sql)

        except Exception as error:
            message = str(error)[:60000]

            try:
                db.query(
                    """
                    UPDATE schema_migrations
                    SET status = 'failed',
                        error_message = %s
                    WHERE filename = %s
                    """,
                    [message, filename],
                )
            except Exception as record_error:
                print(
                    f"[ERROR] Could not record migration failure: "
                    f"{record_error}"
                )

            print(f"[FAILED] {filename}: {error}")
            raise

        db.query(
            """
            UPDATE schema_migrations
            SET status = 'success',
                executed_at = NOW(),
                error_message = NULL
            WHERE filename = %s
            """,
            [filename],
        )

        print(f"[OK] {filename}")
        executed += 1

    print(f"Migration run complete. {executed} migration(s) executed.")

    return executed