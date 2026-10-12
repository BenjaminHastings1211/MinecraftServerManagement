-- Tables for the minecraft database. Safe to re-run.
--
--     mariadb -u minecraftAPI -p minecraft < resources/schema.sql

CREATE TABLE IF NOT EXISTS servers (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    -- Folder under servers/, derived from id (server-004). NULL only
    -- for the moment between inserting the row and naming the folder.
    folder     VARCHAR(32)  NULL,
    status     ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    -- Running processes. *_started is the process start time (Unix
    -- seconds), which tells a live process apart from a reused PID.
    server_pid       INT UNSIGNED NULL,
    server_started   DOUBLE NULL,
    listener_pid     INT UNSIGNED NULL,
    listener_started DOUBLE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY folder (folder)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per player per server: someone on three servers has three rows.
CREATE TABLE IF NOT EXISTS players (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    server_id        INT UNSIGNED NOT NULL,
    uuid             VARCHAR(36)  NOT NULL,
    mc_name          VARCHAR(32)  NOT NULL,
    real_name        VARCHAR(100) NULL,
    first_joined     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    death_count      INT UNSIGNED NOT NULL DEFAULT 0,
    last_death_date  DATETIME NULL,
    -- When they last logged out.
    last_active      DATETIME NULL,
    -- When the current session began; NULL while offline.
    session_start    DATETIME NULL,
    -- Finished sessions only; add the current one for a live total.
    playtime_seconds BIGINT UNSIGNED NOT NULL DEFAULT 0,
    online           BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (id),
    UNIQUE KEY server_player (server_id, mc_name),
    KEY mc_name (mc_name),
    CONSTRAINT players_server FOREIGN KEY (server_id) REFERENCES servers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS locations (
    id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    server_id           INT UNSIGNED NOT NULL,
    created_by          INT UNSIGNED NOT NULL,
    location_name       VARCHAR(100) NOT NULL,
    x_position          INT NOT NULL,
    y_position          INT NOT NULL,
    z_position          INT NOT NULL,
    dimension           VARCHAR(32) NOT NULL DEFAULT 'overworld',
    is_public           BOOLEAN NOT NULL DEFAULT TRUE,
    active              BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,       

    PRIMARY KEY (id),
    INDEX idx_locations_server (server_id),
    INDEX idx_locations_creator (server_id, created_by),
    INDEX idx_locations_public (server_id, is_public, active) 
    ADD UNIQUE KEY uq_location_owner_name (server_id, created_by, location_name);
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
    id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    server_id           INT UNSIGNED NOT NULL,
    created_by          INT UNSIGNED NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    msg_content         VARCHAR(256) NOT NULL,

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sessions (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    player_id INT UNSIGNED NOT NULL,
    server_id INT UNSIGNED NOT NULL, -- might not need
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME NULL,
    duration_seconds INT UNSIGNED NULL,
);

-- PLAYER_ID AND SERVER_ID ARE NOT BOTH NEEDED BC PLAYER_ID IS SERVER DEPENDENT

-- this should be like a activity board people can see what other people need and help out
-- CREATE TABLE IF NOT EXISTS tasks (
--     id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
--     server_id           INT UNSIGNED NOT NULL,
--     created_by          INT UNSIGNED NOT NULL,
--     created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

--     msg_content         VARCHAR(256) NOT NULL,

-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;