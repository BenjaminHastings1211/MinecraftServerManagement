# Minecraft Server Management Tools & Custom Commands

Minecraft server management tools for Raspberry Pi.

## Setup

### 1. Set up commands

From the project root, run:

```bash
./command_setup.sh
```

### 2. Start MariaDB

```bash
sudo systemctl enable --now mariadb
```

### 3. Configure the database

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

### 4. Initialize the database

Run the setup script to load the database schema:

```bash
./mysql_setup
```

This script still needs to be created. It will connect using `.env` and load `resources/schema.sql`.

### 5. Verify setup

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
| `build-rcon` | Restart the RCON utility |
