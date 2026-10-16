"""
Permission levels for players, from the permissions table. See the
004-006 migrations.

    from mcmanager.database import permissions

    if permissions.check_permission(db, 2, "slimshady767", permissions.OP):
        ...

    # Checking several things for one player: look the level up once.
    level = permissions.get_level(db, 2, "slimshady767")
    if permissions.is_allowed(level, permissions.OP):
        ...

Levels stack: a player has every level up to their own, so a
SERVER_ADMIN can do anything an OP can.
"""

PLAYER = 1
OP = 2
SERVER_ADMIN = 3


def get_level(db, server_id, mc_name):
    """The player's permission_id, or None if they have no row."""
    row = db.query(
        "SELECT permission_id FROM players WHERE server_id = %s AND mc_name = %s",
        [server_id, mc_name.strip()],
    ).first()

    return None if row is None else row["permission_id"]


def is_allowed(level, required):
    """
    True if a player at level may do something needing required.
    PLAYER always passes; a level of None (no row) fails anything
    above it.
    """
    if required <= PLAYER:
        return True

    return level is not None and level >= required


def check_permission(db, server_id, mc_name, required):
    """
    is_allowed() for one player, looking up their level only when
    required is above PLAYER.
    """
    if required <= PLAYER:
        return True

    return is_allowed(get_level(db, server_id, mc_name), required)


def set_role(db, server_id, mc_name, permission_id):
    """
    Set a player's permission_id on one server. Raises ValueError if
    they have no row there; an unknown permission_id is rejected by
    the database's foreign key.
    """
    if get_level(db, server_id, mc_name) is None:
        raise ValueError(f"No player {mc_name!r} on server {server_id}.")

    db.query(
        "UPDATE players SET permission_id = %s WHERE server_id = %s AND mc_name = %s",
        [permission_id, server_id, mc_name.strip()],
    )
