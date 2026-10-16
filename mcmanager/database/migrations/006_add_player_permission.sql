ALTER TABLE players
    ADD COLUMN IF NOT EXISTS permission_id SMALLINT NOT NULL DEFAULT 1,
    ADD CONSTRAINT players_permission FOREIGN KEY IF NOT EXISTS (permission_id)
        REFERENCES permissions (permission_id);
