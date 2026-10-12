"""
The servers table: which servers exist, their names, folders and
whether they are active. See schema.sql.

Rows are dicts with the table's columns:
    {"id": 4, "name": "Survival", "folder": "server-004", "status": "active", ...}
"""

from resources.database import Database


ACTIVE = "active"
INACTIVE = "inactive"


def folder_name(number):
    """4 -> 'server-004'."""
    return f"server-{number:03d}"


def get(number):
    """The row for a server number, or None."""
    with Database() as db:
        return db.query("SELECT * FROM servers WHERE id = %s", [number]).first()


def active():
    """Every active server's row, by id."""
    with Database() as db:
        return db.query(
            "SELECT * FROM servers WHERE status = %s ORDER BY id", [ACTIVE]
        ).rows


def add(name):
    """Insert a new active server, give it a folder, and return its row."""
    with Database() as db:
        number = db.query(
            "INSERT INTO servers (name, status) VALUES (%s, %s)", [name, ACTIVE]
        ).lastrowid

        db.query(
            "UPDATE servers SET folder = %s WHERE id = %s",
            [folder_name(number), number],
        )

        return db.query("SELECT * FROM servers WHERE id = %s", [number]).first()


def remove(number):
    """Delete a row outright; only for undoing a failed add()."""
    with Database() as db:
        db.query("DELETE FROM servers WHERE id = %s", [number])


def set_status(number, status):
    with Database() as db:
        db.query("UPDATE servers SET status = %s WHERE id = %s", [status, number])


# The processes a server can have running; see the *_pid columns.
PROCESS_ROLES = ("server", "listener")


def set_process(number, role, pid=None, started=None):
    """Record a running process (or clear it, with no pid)."""
    if role not in PROCESS_ROLES:
        raise ValueError(f"Unknown process role: {role}")

    with Database() as db:
        db.query(
            f"UPDATE servers SET {role}_pid = %s, {role}_started = %s WHERE id = %s",
            [pid, started, number],
        )
