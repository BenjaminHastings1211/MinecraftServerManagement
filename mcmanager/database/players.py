
"""
The players table: one row per player per server, tracking persistent
player information and lifetime statistics. Session state and history
are stored in the sessions table.

Rows returned by lookups include:
    online: Whether the player has an active session.
    session_seconds: Length of the active session so far (0 when offline).

Times come from the database clock, so they agree whichever machine calls in.

The caller owns the Database connection and any transactions.
"""

_SELECT = """
    SELECT p.*,
           (s.id IS NOT NULL) AS online,
           COALESCE(
               GREATEST(
                   TIMESTAMPDIFF(SECOND, s.started_at, NOW()),
                   0
               ),
               0
           ) AS session_seconds
    FROM players AS p
    LEFT JOIN sessions AS s
        ON s.player_id = p.id
        AND s.ended_at IS NULL
"""


def _clean(mc_name):
    mc_name = mc_name.strip()

    if not mc_name:
        raise ValueError("Player name cannot be empty.")

    return mc_name


# Creating

def create(db, server_id, mc_name, real_name=None):
    """Create a player if needed and return their row."""
    mc_name = _clean(mc_name)

    db.query(
        """
        INSERT INTO players (server_id, mc_name, real_name)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE id = id
        """,
        [server_id, mc_name, real_name],
    )

    return get(db, server_id, mc_name)


def set_real_name(db, server_id, mc_name, real_name):
    """Update a player's real name."""
    db.query(
        """
        UPDATE players
        SET real_name = %s
        WHERE server_id = %s
          AND mc_name = %s
        """,
        [real_name, server_id, _clean(mc_name)],
    )


# Lookups

def get(db, server_id, mc_name):
    """Get a player, including derived online status and session time."""
    return db.query(
        _SELECT + """
        WHERE p.server_id = %s
          AND p.mc_name = %s
        """,
        [server_id, _clean(mc_name)],
    ).first()


def on_server(db, server_id):
    """Get all players associated with a server."""
    return db.query(
        _SELECT + """
        WHERE p.server_id = %s
        ORDER BY p.mc_name
        """,
        [server_id],
    ).rows


def online(db, server_id):
    """Get players with an active session on a server."""
    return db.query(
        _SELECT + """
        WHERE p.server_id = %s
          AND s.id IS NOT NULL
        ORDER BY p.mc_name
        """,
        [server_id],
    ).rows


# Statistics

def increment_message_count(db, server_id, mc_name):
    """Increment a player's lifetime message count."""
    return db.query(
        """
        UPDATE players
        SET message_count = message_count + 1
        WHERE server_id = %s
          AND mc_name = %s
        """,
        [server_id, _clean(mc_name)],
    )
