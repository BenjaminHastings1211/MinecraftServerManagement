"""
queries related to server properties
"""

def set_players_reinit_after(db, server_id):
    """Mark existing players for reinitialization."""
    db.query(
        """
        UPDATE servers
        SET players_reinit_after = NOW()
        WHERE id = %s
        """,
        [server_id],
    )


def get_players_reinit_after(db, server_id):
    """Get the server's reinitialization timestamp."""
    result = db.query(
        """
        SELECT players_reinit_after
        FROM servers
        WHERE id = %s
        """,
        [server_id],
    ).first()

    return result["players_reinit_after"] if result else None