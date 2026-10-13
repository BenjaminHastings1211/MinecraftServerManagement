"""
Waypoint management for Minecraft servers.

    from mcmanager.database import locations
    from mcmanager.database.client import DatabaseClient

    with DatabaseClient() as db:
        # Create a waypoint.
        loc = locations.create(
            db=db,
            server_id=2,
            player_id=1,
            name="Home",
            pos=(100, 64, -200),
        )

        # Change waypoint visibility or active status.
        locations.set_public(db, 2, 1, loc["id"], False)
        locations.set_active(db, 2, 1, loc["id"], True)

        # Get locations.
        locations.owned_by(db, 2, 1)
        locations.owned_by_player(db, 2, 5)
        locations.available_to(db, 2, 1)

All functions return dictionaries or lists of dictionaries.
Coordinates are stored as x_position, y_position, z_position.

player_id refers to players.id (the database ID), not the
Minecraft username.

The caller owns the Database connection and any transactions.
"""

_SELECT = "SELECT * FROM locations "


# Creating

def create(db, server_id, player_id, name, pos, dimension="overworld"):
    """
    Create a waypoint or overwrite the existing waypoint with
    the same server, owner, and name.

    Overwriting updates its position and dimension, and resets
    it to public and active.
    """
    name = name.strip()

    if not name:
        raise ValueError("Location name cannot be empty.")

    if len(pos) != 3:
        raise ValueError("Position must contain x, y, and z.")

    x, y, z = (int(value) for value in pos)

    db.query(
        """
        INSERT INTO locations (
            server_id, created_by, location_name,
            x_position, y_position, z_position, dimension,
            is_public, active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, TRUE)
        ON DUPLICATE KEY UPDATE
            x_position = VALUES(x_position),
            y_position = VALUES(y_position),
            z_position = VALUES(z_position),
            dimension = VALUES(dimension),
            is_public = TRUE,
            active = TRUE
        """,
        [server_id, player_id, name, x, y, z, dimension],
    )

    return db.query(
        """
        SELECT *
        FROM locations
        WHERE server_id = %s
          AND created_by = %s
          AND location_name = %s
        """,
        [server_id, player_id, name],
    ).first()


# Updating

def set_active(db, server_id, player_id, location_id, active):
    """
    Set a waypoint's active status.
    Only the owner can change it.
    Returns the updated row, or None if not owned/found.
    """
    db.query(
        """
        UPDATE locations
        SET active = %s
        WHERE id = %s
          AND server_id = %s
          AND created_by = %s
        """,
        [bool(active), location_id, server_id, player_id],
    )

    return db.query(
        _SELECT + """
        WHERE id = %s
          AND server_id = %s
          AND created_by = %s
        """,
        [location_id, server_id, player_id],
    ).first()


def set_public(db, server_id, player_id, location_id, is_public):
    """
    Set a waypoint's public/private status.
    Only the owner can change it.
    Returns the updated row, or None if not owned/found.
    """
    db.query(
        """
        UPDATE locations
        SET is_public = %s
        WHERE id = %s
          AND server_id = %s
          AND created_by = %s
        """,
        [bool(is_public), location_id, server_id, player_id],
    )

    return db.query(
        _SELECT + """
        WHERE id = %s
          AND server_id = %s
          AND created_by = %s
        """,
        [location_id, server_id, player_id],
    ).first()


# Looking up locations

def owned_by(db, server_id, player_id):
    """
    Get all active locations owned by this player,
    including public and private locations.
    """
    return db.query(
        _SELECT + """
        WHERE server_id = %s
          AND created_by = %s
          AND active = TRUE
        ORDER BY location_name
        """,
        [server_id, player_id],
    ).rows


def owned_by_player(db, server_id, player_id):
    """
    Get another player's public, active locations.
    Private and inactive locations are excluded.
    """
    return db.query(
        _SELECT + """
        WHERE server_id = %s
          AND created_by = %s
          AND is_public = TRUE
          AND active = TRUE
        ORDER BY location_name
        """,
        [server_id, player_id],
    ).rows


def available_to(db, server_id, player_id):
    """
    Get all public, active locations plus this player's
    private, active locations.

    Ordering:
      1. This player's private locations.
      2. All public locations, including their own.

    Inactive locations are excluded.
    """
    return db.query(
        _SELECT + """
        WHERE server_id = %s
          AND active = TRUE
          AND (is_public = TRUE OR created_by = %s)
        ORDER BY
            (created_by = %s AND is_public = FALSE) DESC,
            location_name ASC
        """,
        [server_id, player_id, player_id],
    ).rows


def get(db, server_id, player_id, name):
    """Get one location owned by a player, or None."""
    return db.query(
        """
        SELECT *
        FROM locations
        WHERE server_id = %s
          AND created_by = %s
          AND location_name = %s
        """,
        [server_id, player_id, name],
    ).first()