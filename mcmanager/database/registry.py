"""
The servers table: which servers exist, their names, folders and
whether they are active. See schema.sql.

Rows are dicts with the table's columns:
    {"id": 4, "name": "Survival", "folder": "server-004", "status": "active", ...}
"""

ACTIVE = "active"
INACTIVE = "inactive"


def folder_name(server_id):
    """4 -> 'server-004'."""
    return f"server-{server_id:03d}"


def get(db, server_id):
    """The row for a server id, or None."""
    return db.query("SELECT * FROM servers WHERE id = %s", [server_id]).first()


def active(db):
    """Every active server's row, by id."""
    return db.query(
        "SELECT * FROM servers WHERE status = %s ORDER BY id", [ACTIVE]
    ).rows


def add(db, name):
    """Insert a new active server, give it a folder, and return its row."""
    server_id = db.query(
        "INSERT INTO servers (name, status) VALUES (%s, %s)", [name, ACTIVE]
    ).lastrowid

    db.query(
        "UPDATE servers SET folder = %s WHERE id = %s",
        [folder_name(server_id), server_id],
    )

    return get(db, server_id)


def remove(db, server_id):
    """Delete a row outright; only for undoing a failed add()."""
    db.query("DELETE FROM servers WHERE id = %s", [server_id])


def set_status(db, server_id, status):
    db.query(
        "UPDATE servers SET status = %s WHERE id = %s",
        [status, server_id],
    )


# The processes a server can have running; see the *_pid columns.
PROCESS_ROLES = ("server", "listener")


def set_process(db, server_id, role, pid=None, started=None):
    """Record a running process (or clear it, with no pid)."""
    if role not in PROCESS_ROLES:
        raise ValueError(f"Unknown process role: {role}")

    db.query(
        f"UPDATE servers SET {role}_pid = %s, {role}_started = %s WHERE id = %s",
        [pid, started, server_id],
    )