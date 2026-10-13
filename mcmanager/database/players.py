"""
The players table: one row per player per server, tracking sessions
and playtime. See schema.sql.

    from mcmanager.database import players
    from mcmanager.database.client import DatabaseClient

    with DatabaseClient() as db:
        players.login(db, 2, "slimshady767")
        seconds = players.logout(db, 2, "slimshady767")

        for player in players.online(db, 2):
            print(player["mc_name"], player["session_seconds"])

Rows are dicts with the table's columns plus session_seconds, the
length of the current session so far (0 when offline). Times come
from the database clock, so they agree whichever machine calls in.

The caller owns the Database connection and any transactions.
"""

_SELECT = """
    SELECT *,
           IF(online, TIMESTAMPDIFF(SECOND, session_start, NOW()), 0)
               AS session_seconds
    FROM players
"""


def _clean(mc_name):
    mc_name = mc_name.strip()

    if not mc_name:
        raise ValueError("Player name cannot be empty.")

    return mc_name


# Creating

def create(db, server_id, mc_name, real_name=None, first_joined=None):
    """
    Add a player to a server and return their row. If they are
    already on that server, the existing row is returned unchanged.
    first_joined defaults to now.
    """
    mc_name = _clean(mc_name)

    db.query(
        "INSERT INTO players (server_id, mc_name, real_name, first_joined) "
        "VALUES (%s, %s, %s, COALESCE(%s, NOW())) "
        "ON DUPLICATE KEY UPDATE id = id",
        [server_id, mc_name, real_name, first_joined],
    )

    return db.query(
        _SELECT + "WHERE server_id = %s AND mc_name = %s",
        [server_id, mc_name],
    ).first()


def set_real_name(db, server_id, mc_name, real_name):
    db.query(
        "UPDATE players SET real_name = %s WHERE server_id = %s AND mc_name = %s",
        [real_name, server_id, _clean(mc_name)],
    )


# Sessions

def login(db, server_id, mc_name, at=None):
    """
    Start a session: online, session_start = at (a datetime;
    default now). The player is created if this is their first time
    on the server.

    If they were already online (e.g. logout never ran), that
    unfinished session is counted towards playtime first.

    The caller should use a transaction if the whole login operation
    needs to be atomic.
    """
    player = create(db, server_id, mc_name, first_joined=at)

    db.query(
        """
        UPDATE players
        SET playtime_seconds = playtime_seconds + IF(
                online AND session_start IS NOT NULL,
                GREATEST(TIMESTAMPDIFF(SECOND, session_start, COALESCE(%s, NOW())), 0),
                0
            ),
            session_start = COALESCE(%s, NOW()),
            online = TRUE
        WHERE id = %s
        """,
        [at, at, player["id"]],
    )

    return db.query(
        _SELECT + "WHERE id = %s",
        [player["id"]],
    ).first()


def logout(db, server_id, mc_name, at=None):
    """
    End a session at `at` (a datetime; default now): its length is
    added to playtime_seconds, the player goes offline and
    last_active becomes `at`.

    Returns the session length in seconds, or None if the player
    wasn't online (or doesn't exist).

    The caller should use a transaction because this operation reads
    the active session before updating the player.
    """
    player = db.query(
        """
        SELECT id,
               GREATEST(
                   COALESCE(TIMESTAMPDIFF(SECOND, session_start, COALESCE(%s, NOW())), 0),
                   0
               ) AS seconds
        FROM players
        WHERE server_id = %s
          AND mc_name = %s
          AND online
        FOR UPDATE
        """,
        [at, server_id, _clean(mc_name)],
    ).first()

    if player is None:
        return None

    seconds = player["seconds"] or 0

    db.query(
        """
        UPDATE players
        SET playtime_seconds = playtime_seconds + %s,
            session_start = NULL,
            online = FALSE,
            last_active = COALESCE(%s, NOW())
        WHERE id = %s
        """,
        [seconds, at, player["id"]],
    )

    return seconds


def logout_all(db, server_id):
    """
    Log out everyone still online on a server, e.g. when it stops.
    Returns {mc_name: session seconds}.
    """
    return {
        player["mc_name"]: logout(db, server_id, player["mc_name"])
        for player in online(db, server_id)
    }


# Lookups

def get(db, server_id, mc_name):
    """A player's row on one server, or None."""
    return db.query(
        _SELECT + "WHERE server_id = %s AND mc_name = %s",
        [server_id, _clean(mc_name)],
    ).first()


def on_server(db, server_id):
    """Every player who has been on a server, by name."""
    return db.query(
        _SELECT + "WHERE server_id = %s ORDER BY mc_name",
        [server_id],
    ).rows


def online(db, server_id):
    """Players currently online on a server, by name."""
    return db.query(
        _SELECT + "WHERE server_id = %s AND online ORDER BY mc_name",
        [server_id],
    ).rows