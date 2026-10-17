ALTER TABLE players
    DROP FOREIGN KEY players_server,
    ADD CONSTRAINT fk_players_server_cascade
        FOREIGN KEY (server_id)
        REFERENCES servers (id)
        ON DELETE CASCADE;