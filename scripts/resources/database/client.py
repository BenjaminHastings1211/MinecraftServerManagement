"""
Client for the local MariaDB/MySQL 'minecraft' database.

    with DatabaseClient() as db:
        db.query("INSERT INTO players (name) VALUES (%s)", ["Steve"])
        result = db.query("SELECT * FROM players WHERE name = %s", ["Steve"])

        for row in result.rows:
            print(row["name"])

Always pass values through params (the %s placeholders) rather than
formatting them into the SQL string; the driver escapes them safely.

Connection settings can be overridden with the MC_DB_HOST, MC_DB_PORT,
MC_DB_USER, MC_DB_PASSWORD and MC_DB_NAME environment variables.
"""

import os
from dotenv import load_dotenv
from contextlib import contextmanager
from dataclasses import dataclass, field
import pymysql
import pymysql.cursors


load_dotenv()

HOST = os.environ.get("DB_HOST", "127.0.0.1")
PORT = int(os.environ.get("DB_PORT", "3306"))
USER = os.environ.get("DB_USER", "")
PASSWORD = os.environ.get("DB_PASSWORD", "")
NAME = os.environ.get("DB_NAME", "minecraft")

class DatabaseError(RuntimeError):
    pass


@dataclass
class Result:
    """
    What a query returned.

    columns   column names, in order (empty for INSERT/UPDATE/etc.)
    rows      one dict per row, keyed by column name
    rowcount  rows returned, or rows affected for writes
    lastrowid AUTO_INCREMENT id of the last inserted row, if any
    """

    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    rowcount: int = 0
    lastrowid: int | None = None

    def first(self):
        """The first row, or None."""
        return self.rows[0] if self.rows else None

    def scalar(self):
        """The first column of the first row, or None."""
        row = self.first()
        return next(iter(row.values())) if row else None


class DatabaseClient:
    def __init__(self, host=HOST, port=PORT, user=USER, password=PASSWORD,
                 database=NAME, timeout=5):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.timeout = timeout
        self._connection = None

    def connect(self):
        try:
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=self.timeout,
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
                autocommit=True,
            )
        except pymysql.MySQLError as error:
            raise DatabaseError(
                f"Cannot connect to database '{self.database}' as "
                f"{self.user}@{self.host}:{self.port} ({_message(error)})."
            ) from None

    def query(self, sql, params=None):
        """Run one SQL statement and return a Result."""
        if self._connection is None:
            raise DatabaseError("Not connected.")

        try:
            # Reconnects if the server dropped an idle connection.
            self._connection.ping(reconnect=True)

            with self._connection.cursor() as cursor:
                cursor.execute(sql, params)

                columns = [column[0] for column in cursor.description or ()]
                rows = list(cursor.fetchall()) if cursor.description else []

                return Result(
                    columns=columns,
                    rows=rows,
                    rowcount=cursor.rowcount,
                    lastrowid=cursor.lastrowid or None,
                )
        except pymysql.MySQLError as error:
            raise DatabaseError(_message(error)) from None

    @contextmanager
    def transaction(self):
        """
        Group queries so they all apply or none do:

            with db.transaction():
                db.query("SELECT ... FOR UPDATE")
                db.query("UPDATE ...")
        """
        self.query("START TRANSACTION")

        try:
            yield self
        except BaseException:
            self._connection.rollback()
            raise

        self.query("COMMIT")

    def close(self):
        if self._connection is not None:
            try:
                self._connection.close()
            except pymysql.MySQLError:
                pass

            self._connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()


def query(sql, params=None):
    """One-off query on a fresh connection."""
    with DatabaseClient() as db:
        return db.query(sql, params)


def _message(error):
    """'(1146, "Table 'x' doesn't exist")' -> "Table 'x' doesn't exist"."""
    if len(error.args) >= 2:
        return str(error.args[1])

    return str(error)
