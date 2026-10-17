ALTER TABLE locations
    ADD CONSTRAINT fk_locations_creator
        FOREIGN KEY (created_by)
        REFERENCES players (id)
        ON DELETE CASCADE;