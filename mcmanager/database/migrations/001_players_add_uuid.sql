-- Add the player's Minecraft UUID. Nullable: existing rows have none yet.
-- Idempotent (IF NOT EXISTS), so it is safe to retry.
ALTER TABLE players ADD COLUMN IF NOT EXISTS uuid VARCHAR(36) NULL AFTER server_id;
