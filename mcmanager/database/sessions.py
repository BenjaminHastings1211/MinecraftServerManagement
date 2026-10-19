
"""Session history for Minecraft players.

Each row represents one player session on a server.

    from mcmanager.database import sessions
    from mcmanager.database.client import DatabaseClient

    with DatabaseClient() as db:
        session = sessions.start(db, 2, "slimshady767")
        session = sessions.end(db, 2, "slimshady767")

        for session in sessions.history(db, 2, "slimshady767"):
            print(session["started_at"], session["duration_seconds"])

The caller owns the Database connection and any transactions.
"""

from mcmanager.database import players


# Creating / ending sessions

def start(db, server_id, mc_name, at=None):
    """Start a session and return its row.

    If the player already has an active session, close it first
    as interrupted before creating the new session.
    """
    # Reconcile a stale active session, if one exists.
    active = get_active(db, server_id, mc_name)

    if active is not None:
        end(db, server_id, mc_name, at=at, reason="RECOVERY")

    player = players.get(db, server_id, mc_name)

    db.query(
        """
        INSERT INTO sessions (player_id, server_id, started_at)
        VALUES (%s, %s, COALESCE(%s, NOW()))
        """,
        [player["id"], server_id, at],
    )

    return get_active(db, server_id, mc_name)


def end(db, server_id, mc_name, at=None, reason="DISCONNECT"):
    """End the active session and update the player's total playtime.

    Returns the ended session row, or None if no session is active.
    """
    session = get_active(db, server_id, mc_name)

    if session is None:
        return None

    db.query(
        """
        UPDATE sessions
        SET ended_at = COALESCE(%s, NOW()),
            duration_seconds = GREATEST(
                TIMESTAMPDIFF(
                    SECOND,
                    started_at,
                    COALESCE(%s, NOW())
                ),
                0
            ),
            end_reason = %s
        WHERE id = %s
          AND ended_at IS NULL
        """,
        [at, at, reason, session["id"]],
    )

    # Get the calculated duration from the session record.
    session = get(db, session["id"])
    seconds = session["duration_seconds"] or 0

    player = players.get(db, server_id, mc_name)

    if player is not None:
        db.query(
            """
            UPDATE players
            SET playtime_seconds = playtime_seconds + %s
            WHERE id = %s
            """,
            [seconds, player["id"]],
        )

    return session


def recover(db, server_id, at=None):
    """Close all active sessions after a server/listener restart.

    Returns the number of sessions recovered.
    """
    active_sessions = db.query(
        """
        SELECT id, player_id
        FROM sessions
        WHERE server_id = %s
          AND ended_at IS NULL
        """,
        [server_id],
    ).rows

    for session in active_sessions:
        db.query(
            """
            UPDATE sessions
            SET ended_at = COALESCE(%s, NOW()),
                duration_seconds = GREATEST(
                    TIMESTAMPDIFF(
                        SECOND,
                        started_at,
                        COALESCE(%s, NOW())
                    ),
                    0
                ),
                end_reason = 'RECOVERY'
            WHERE id = %s
              AND ended_at IS NULL
            """,
            [at, at, session["id"]],
        )

        db.query(
            """
            UPDATE players p
            JOIN sessions s ON s.player_id = p.id
            SET p.playtime_seconds = p.playtime_seconds + COALESCE(s.duration_seconds, 0)
            WHERE s.id = %s
            """,
            [session["id"]],
        )

    return len(active_sessions)


# Lookups

def get(db, session_id):
    """Get a session by ID, or None."""
    return db.query(
        "SELECT * FROM sessions WHERE id = %s",
        [session_id],
    ).first()

def get_active(db, server_id, mc_name):
    """Get a player's active session on a server, or None."""
    return db.query(
        """
        SELECT s.*
        FROM sessions AS s
        JOIN players AS p ON p.id = s.player_id
        WHERE s.server_id = %s
          AND p.mc_name = %s
          AND s.ended_at IS NULL
        ORDER BY s.started_at DESC
        LIMIT 1
        """,
        [server_id, mc_name.strip()],
    ).first()

def active(db, server_id):
    """Return all active sessions on a server."""
    return db.query(
        """
        SELECT s.*, p.mc_name
        FROM sessions AS s
        JOIN players AS p ON p.id = s.player_id
        WHERE s.server_id = %s
          AND s.ended_at IS NULL
        ORDER BY s.started_at
        """,
        [server_id],
    ).rows

# metrics

def playtime_summary(db, server_id, interval):
    """
    Get each player's playtime over the given interval.

    Args:
        db: Database connection.
        server_id: Server ID.
        interval: MySQL interval value, e.g. "7 DAY", "1 MONTH".

    Returns:
        Rows containing player_id, mc_name, and playtime_seconds,
        ordered by most playtime.
    """
    return db.query(
        """
        SELECT
            p.id AS player_id,
            p.mc_name,
            COALESCE(SUM(
                GREATEST(
                    0,
                    TIMESTAMPDIFF(
                        SECOND,
                        GREATEST(s.started_at, NOW() - INTERVAL %s),
                        LEAST(COALESCE(s.ended_at, NOW()), NOW())
                    )
                )
            ), 0) AS playtime_seconds
        FROM players AS p
        LEFT JOIN sessions AS s
            ON s.player_id = p.id
            AND s.server_id = p.server_id
            AND s.started_at < NOW()
            AND COALESCE(s.ended_at, NOW()) > NOW() - INTERVAL %s
        WHERE p.server_id = %s
        GROUP BY p.id, p.mc_name
        ORDER BY playtime_seconds DESC
        """,
        [interval, interval, server_id],
    ).rows