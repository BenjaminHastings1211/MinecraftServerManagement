ALTER TABLE players
    DROP COLUMN IF EXISTS session_start,
    DROP COLUMN IF EXISTS first_joined,
    DROP COLUMN IF EXISTS last_active;