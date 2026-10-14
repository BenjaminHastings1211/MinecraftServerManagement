# Minecraft Server Management Tools & Custom Commands

Minecraft server management tools for Raspberry Pi.

## Setup

### 1. Clone the repository

Clone the repository and navigate to the project directory.

### 2. Set up the Python environment

Create a virtual environment in the project root and install the dependencies into it:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

You don't need to activate it. Every script switches to `.venv/bin/python` on its own (see `scripts/_bootstrap.py`), whichever directory you run it from.

### 3. Set up commands

From the project root, run:

```bash
./command_setup.sh
```

### 4. Start MariaDB

Enable MariaDB to start automatically and start it now:

```bash
sudo systemctl enable --now mariadb
```

### 5. Configure the database

Create a `.env` file in the project root:

```bash
nano .env
```

Add your database credentials:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=minecraftAPI
DB_PASSWORD=YOUR_DATABASE_PASSWORD
DB_NAME=minecraft
```

### 6. Initialize the database

Run the setup script to load the database schema:

```bash
./mysql_setup.py
```

It uses `.env` to connect to MariaDB and load the database schema. Then apply any migrations:

```bash
./db_upgrade.py --dry-run   # list what would run
./db_upgrade.py
```

### 7. Verify setup

Start a Minecraft server:

```bash
mc-start
```

## Commands

| Command | Description |
|---|---|
| `mc-confirm` | Confirm the Minecraft EULA |
| `mc-create` | Create a server |
| `mc-delete` | Delete a server |
| `mc-list` | List servers |
| `mc-start` | Start a server |
| `mc-stop` | Stop a server |
| `mc-upgrade` | Upgrade a server |
| `mc-backup` | Manage server backups |
| `mc-config` | Configure a server |
| `mc-monitor` | Monitor a server |
| `mc-cmd` | Send a Minecraft command |
| `build-rcon` | Restart the RCON utility (`-q` to skip the in-game message) |

## Project layout

```text
scripts/            Command entry points (symlinked into /usr/local/bin)
  _bootstrap.py     Imported first by every script: uses .venv, finds mcmanager
mcmanager/          Shared code
  paths.py          Project locations (servers/, versions/, .env, .venv)
  server.py         The Server class: config, properties, RCON, processes
  backup.py         World backups and restore
  versions.py       Server JARs and Mojang downloads
  cli.py            Shared argument parsing and output
  listener/         Log listener (python -m mcmanager.listener <id>) and events
  database/         MariaDB client, table modules, schema.sql, migrations/
servers/            Server instances (runtime data, not in git)
versions/           Server JARs (runtime data, not in git)
```

## Database migrations

Schema changes go in `mcmanager/database/migrations/` as numbered SQL files
(`002_add_something.sql`), one statement per file. `./db_upgrade.py` runs the ones
that haven't succeeded yet and records each in the `schema_migrations` table.

MariaDB can't roll back DDL, so write statements that are safe to re-run
(`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, ...). Also update
`schema.sql` so fresh installs match. See `migrate.py` for details.
