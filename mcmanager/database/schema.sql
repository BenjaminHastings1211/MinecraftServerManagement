-- Tables for the minecraft database. Safe to re-run.

CREATE TABLE IF NOT EXISTS servers (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    folder     VARCHAR(32) NULL,
    status     ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    has_init   BOOLEAN NOT NULL DEFAULT FALSE,
    server_pid       INT UNSIGNED NULL,
    server_started   DOUBLE NULL,
    listener_pid     INT UNSIGNED NULL,
    listener_started DOUBLE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY folder (folder)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS permissions (
    permission_id SMALLINT PRIMARY KEY,
    name          VARCHAR(32) NOT NULL UNIQUE,
    description   TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO permissions (permission_id, name, description)
VALUES
    (1, 'PLAYER', 'Standard player permissions'),
    (2, 'OP', 'Minecraft operator permissions'),
    (3, 'SERVER_ADMIN', 'Server controller administration permissions');


CREATE TABLE IF NOT EXISTS players (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    server_id        INT UNSIGNED NOT NULL,
    uuid             VARCHAR(36) NULL,
    mc_name          VARCHAR(32) NOT NULL,
    real_name        VARCHAR(100) NULL,
    death_count      INT UNSIGNED NOT NULL DEFAULT 0,
    last_death_date  DATETIME NULL,
    playtime_seconds BIGINT UNSIGNED NOT NULL DEFAULT 0,
    message_count    BIGINT NOT NULL DEFAULT 0,
    permission_id    SMALLINT NOT NULL DEFAULT 1,

    PRIMARY KEY (id),
    UNIQUE KEY server_player (server_id, mc_name),
    KEY mc_name (mc_name),

    CONSTRAINT players_server
        FOREIGN KEY (server_id)
        REFERENCES servers (id)
        ON DELETE CASCADE,

    CONSTRAINT players_permission
        FOREIGN KEY (permission_id)
        REFERENCES permissions (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS locations (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    server_id      INT UNSIGNED NOT NULL,
    created_by     INT UNSIGNED NOT NULL,
    location_name  VARCHAR(100) NOT NULL,
    x_position     INT NOT NULL,
    y_position     INT NOT NULL,
    z_position     INT NOT NULL,
    dimension      VARCHAR(32) NOT NULL DEFAULT 'overworld',
    is_public      BOOLEAN NOT NULL DEFAULT TRUE,
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_locations_server (server_id),
    INDEX idx_locations_creator (server_id, created_by),
    INDEX idx_locations_public (server_id, is_public, active),
    UNIQUE KEY uq_location_owner_name
        (server_id, created_by, location_name),

    CONSTRAINT fk_locations_server
        FOREIGN KEY (server_id)
        REFERENCES servers (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_locations_creator
        FOREIGN KEY (created_by)
        REFERENCES players (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS sessions (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    player_id        INT UNSIGNED NOT NULL,
    server_id        INT UNSIGNED NOT NULL,
    started_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at         DATETIME NULL,
    duration_seconds INT UNSIGNED NULL,
    end_reason       VARCHAR(32) NULL,

    PRIMARY KEY (id),
    INDEX idx_sessions_player_history (player_id, started_at),
    INDEX idx_sessions_server_history (server_id, started_at),
    INDEX idx_sessions_active (server_id, player_id, ended_at),

    CONSTRAINT fk_sessions_player
        FOREIGN KEY (player_id)
        REFERENCES players (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_sessions_server
        FOREIGN KEY (server_id)
        REFERENCES servers (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS schema_migrations (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    filename      VARCHAR(255) NOT NULL,
    status        ENUM('pending', 'running', 'success', 'failed')
                  NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at    DATETIME NULL,
    executed_at   DATETIME NULL,
    error_message TEXT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_migration_filename (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
