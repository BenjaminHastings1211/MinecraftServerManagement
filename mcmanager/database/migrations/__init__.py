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

def run(db, dry_run=False):
    """
    Run pending SQL migrations in filename order.

    Migrations with pending or failed status are retried.
    Successful migrations are skipped.

    Args:
        db: An open DatabaseClient connection.
        dry_run: Show pending migrations without changing the database.

    Returns:
        Number of migrations successfully executed.
    """
    migrations_dir = Path(__file__).resolve().parent

    if not dry_run:
        ensure_table(db)

    applied = {
        row["filename"]: row["status"]
        for row in db.query(
            "SELECT filename, status FROM schema_migrations"
        ).rows
    } if not dry_run else {}

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

        if dry_run:
            print(f"[DRY RUN] Would execute {filename}")
            continue

        # Ensure the migration is recorded before attempting its SQL.
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

    if dry_run:
        print("Dry run complete. No migrations executed.")
    else:
        print(f"Migration run complete. {executed} migration(s) executed.")

    return executed