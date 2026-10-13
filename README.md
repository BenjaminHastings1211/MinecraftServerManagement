# Minecraft Server Management Tools & Custom Commands

Minecraft server management tools for Raspberry Pi.

## Setup

### 1. Clone the repository

Clone the repository and navigate to the project directory.

### 2. Set up the Python environment

Create and activate a virtual environment, then install the required dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

**Note:** Activate the virtual environment whenever you work on the project so the scripts can access the installed dependencies.

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

Ensure the setup script exists and is executable. It uses `.env` to connect to MariaDB and load the database schema.

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
| `build-rcon` | Restart the RCON utility |
