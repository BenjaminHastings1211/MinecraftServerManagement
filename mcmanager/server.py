import json
import re
import secrets
import shutil
import subprocess
import sys
import time
import uuid

from datetime import datetime
from pathlib import Path

import psutil

from mcmanager.database import registry, sessions
from mcmanager.database.client import DatabaseClient
from mcmanager.console import Console, strip_formatting
from mcmanager.properties import Properties
from mcmanager import backup as _backup
from mcmanager.rcon import Rcon, RconError
from mcmanager.paths import ROOT, SERVERS, DEFAULTS, VENV_PYTHON
from mcmanager.versions import find_version_jar, filename_to_version


LISTENER_MODULE = "mcmanager.listener"

# Where the listener lived before the restructure, so a listener started
# by the old code is still recognised (and stopped) rather than duplicated.
LEGACY_LISTENER = ROOT / "scripts" / "resources" / "listener.py"

DEFAULT_PORT = 25565
DEFAULT_RCON_PORT = 25575

READY_TIMEOUT = 300

_PLAYER_LIST = re.compile(r"There are (\d+) of a max of (\d+) players online:\s*(.*)")

JVM_FLAGS = [
    "-XX:+UseG1GC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+DisableExplicitGC",
    "-XX:+AlwaysPreTouch",
]


def parse_server_id(value):
    """
    Normalise a server ID to its database id: 3, "3", "003" and
    "server-003" all become 3.
    """
    text = str(value).strip().lower().removeprefix("server-")

    try:
        number = int(text)
    except ValueError:
        raise ValueError(f"Invalid server ID: {value}") from None

    if number < 1:
        raise ValueError("Server ID must be positive.")

    return number


def used_ports():
    """Every game and RCON port claimed by any server."""
    ports = set()

    for server in Server.all():
        ports.update(
            port for port in (server.port, server.rcon_port)
            if port is not None
        )

    return ports


def next_free_port(start):
    used = used_ports()
    port = start

    while port in used:
        port += 1

    return port


def get_next_port():
    return next_free_port(DEFAULT_PORT)


def _directory_size(path):
    total = 0

    for file in path.rglob("*"):
        try:
            if file.is_file() and not file.is_symlink():
                total += file.stat().st_size
        except OSError:
            # Files can vanish mid-scan while the server is running.
            continue

    return total


class Server:
    """
    A Minecraft server living in SERVERS/<folder>.

    Every server has a row in the database's servers table (see
    registry.py) holding its auto-assigned id, name, folder and
    status. Only active servers can be loaded.

    config.json holds the settings managed by these scripts.
    Its "properties" section holds server.properties overrides,
    applied every time the server starts. Keys and values use the
    exact names and text form found in server.properties, e.g.
    "server-port": "25565", "white-list": "false".
    """

    def __init__(self, server_id, record=None):
        if record is None:
            server_id = parse_server_id(server_id)
            with DatabaseClient() as db:
                record = registry.get(db, server_id)

            if record is None or record["status"] != registry.ACTIVE:
                raise FileNotFoundError(f"Server not found: {server_id}")

        self.record = record
        self.id = record["id"]
        self.folder = record["folder"]
        self.path = SERVERS / self.folder
        self.config_path = self.path / "config.json"
        self.properties_path = self.path / "server.properties"
        self.eula_path = self.path / "eula.txt"
        self.log_path = self.path / "console.log"
        self.listener_log_path = self.path / "listener.log"
        self.backups_path = self.path / "backups"
        self.db = DatabaseClient()

        if not self.path.is_dir():
            raise FileNotFoundError(f"Server not found: {self.folder}")

        self._load_config()

    def __repr__(self):
        return f"Server({self.id!r}, name={self.name!r}, folder={self.folder!r})"

    @classmethod
    def all(cls):
        """Every active server, sorted by ID. Broken ones are skipped."""
        servers = []
        with DatabaseClient() as db:
            for record in registry.active(db):
                try:
                    servers.append(cls(record["id"], record))
                except (OSError, ValueError):
                    continue

        return servers

    @classmethod
    def create(cls, name, version=None):
        """
        Register a new server in the database, which assigns its ID
        and folder, then create its files from defaults.json and
        generate server.properties and eula.txt. The EULA still has
        to be accepted before it can start.
        """
        name = name.strip()

        if not name:
            raise ValueError("Server name cannot be empty.")

        with DEFAULTS.open("r") as file:
            config = json.load(file)

        jar = find_version_jar(version)
        with DatabaseClient() as db:
            record = registry.add(db, name)
        server_path = SERVERS / record["folder"]

        try:
            server_path.mkdir(parents=True)
        except BaseException:
            with DatabaseClient() as db:
                registry.remove(db, record["id"])
                raise

        try:
            shutil.copy2(jar, server_path / "server.jar")
            cls._init_settings(server_path)

            config["create_date"] = datetime.now().isoformat()
            config["version"] = filename_to_version(jar)

            properties = config.setdefault("properties", {})
            properties["server-port"] = str(get_next_port())
            properties["motd"] = name

            with (server_path / "config.json").open("w") as file:
                json.dump(config, file, indent=4)

            server = cls(record["id"], record)
            server.ensure_rcon()
            server.configure_properties()

        except BaseException:
            shutil.rmtree(server_path, ignore_errors=True)

            with DatabaseClient() as db:
                registry.remove(db, record["id"])
            
            raise

        return server

    @staticmethod
    def _init_settings(server_path):
        """Have Minecraft write server.properties and eula.txt, then exit."""
        result = subprocess.run(
            ["java", "-jar", "server.jar", "--initSettings", "--nogui"],
            cwd=server_path,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0 or not (server_path / "server.properties").is_file():
            output = (result.stdout + result.stderr).strip().splitlines()
            raise RuntimeError(
                "Failed to initialise server files:\n"
                + "\n".join(output[-10:])
            )

    # Config

    def _load_config(self):
        with self.config_path.open("r") as file:
            self.config = json.load(file)

        self.config.setdefault("properties", {})

    def save(self):
        temp_path = self.config_path.with_name("config.json.tmp")

        with temp_path.open("w") as file:
            json.dump(self.config, file, indent=4)

        temp_path.replace(self.config_path)

    def close(self):
        self.save()

    @property
    def name(self):
        return self.record["name"]

    @property
    def version(self):
        return self.config.get("version", "Unknown")

    def get_property(self, key, default=None):
        """A server.properties value, with config.json overrides applied."""
        value = self.config["properties"].get(key)

        if value is None and self.properties_path.is_file():
            value = self.server_properties().get(key)

        return default if value is None else value

    def _int_property(self, key):
        try:
            return int(self.get_property(key))
        except (TypeError, ValueError):
            return None

    @property
    def port(self):
        return self._int_property("server-port")

    @property
    def rcon_port(self):
        if self.get_property("enable-rcon") != "true":
            return None

        return self._int_property("rcon.port")

    @property
    def created(self):
        """Creation time as a datetime, or None if unknown."""
        try:
            return datetime.fromisoformat(self.config["create_date"])
        except (KeyError, TypeError, ValueError):
            return None

    # server.properties

    def server_properties(self):
        return Properties(self.properties_path)

    def configure_properties(self):
        """
        Apply config.json overrides to server.properties.

        Returns the override keys that don't exist in
        server.properties (and so were not applied).
        """
        if not self.properties_path.is_file():
            return []

        with self.server_properties() as properties:
            return properties.update(self.config["properties"])

    def unknown_properties(self):
        """Override keys in config.json that Minecraft doesn't recognise."""
        if not self.properties_path.is_file():
            return []

        keys = self.server_properties().keys()

        return [key for key in self.config["properties"] if key not in keys]

    # EULA

    def eula_approved(self):
        if not self.eula_path.is_file():
            return False

        with self.eula_path.open("r") as file:
            return any(line.strip() == "eula=true" for line in file)

    def accept_eula(self):
        lines = []

        if self.eula_path.is_file():
            with self.eula_path.open("r") as file:
                lines = [
                    line for line in file
                    if not line.strip().startswith("eula=")
                ]

        lines.append("eula=true\n")
        self.eula_path.write_text("".join(lines))

    # RCON

    def ensure_rcon(self):
        """
        Give this server RCON settings (enabled, own port, random
        password) if it lacks them. Returns True if anything changed;
        a running server only picks them up on its next start.
        """
        properties = self.config["properties"]
        wanted = {"enable-rcon": "true"}

        if not properties.get("rcon.password"):
            wanted["rcon.password"] = secrets.token_urlsafe(24)

        if "rcon.port" not in properties:
            wanted["rcon.port"] = str(next_free_port(DEFAULT_RCON_PORT))

        changed = {
            key: value for key, value in wanted.items()
            if properties.get(key) != value
        }

        if not changed:
            return False

        properties.update(changed)
        self.save()
        return True

    def rcon(self):
        """
        An unconnected Rcon client; use as a context manager:

            with server.rcon() as rcon:
                rcon.command("list")
        """
        if not self.is_running():
            raise RconError(f"{self.name} ({self.folder}) is not running.")

        port = self.rcon_port
        password = self.config["properties"].get("rcon.password")

        if port is None or not password:
            raise RconError(f"RCON is not configured for {self.folder}.")

        return Rcon("127.0.0.1", port, password, lock_path=self.path / ".rcon.lock")

    def console(self):
        """
        A two-way Console (RCON commands + live log); use as a
        context manager. See mcmanager/console.py.
        """
        return Console(self)

    def initialize(self):
        """ this function will run once when the server is booted for the first time """

        self.command("scoreboard objectives add deaths deathCount")

    def command(self, command):
        """Run one server command over RCON and return its reply."""
        with self.rcon() as rcon:
            reply = rcon.command(command.strip().removeprefix("/"))

        return strip_formatting(reply).strip()

    def notify(self, message):
        """
        Send a specially formatted message (see messages/base.py).
        Returns True if delivered, False if the target isn't online.
        """
        reply = self.command(str(message))

        if not reply:
            return True

        if reply == "No player was found":
            return False

        if reply.startswith("Showing new "):
            return True

        raise RuntimeError(f"notify failed: {reply}")

    def get_death_count(self, player):
        """
        Return player death count, or 0 if failed to regex match. (usually happens if deaths is 0)
        """
        response = self.command(
            "scoreboard players get %s deaths" % player
        )

        match = re.search(r"has (-?\d+)", str(response))
        return int(match.group(1)) if match else 0

    def get_player_dimension(self, player):
        resp = self.command(f"data get entity {player} Dimension")
        match = re.search(r'"(?P<dimension>minecraft:[^"]+)"', str(resp))

        return match.group("dimension") if match else None


    def get_player_pos(self, player):
        resp = self.command(f"data get entity {player} Pos")
        match = re.search(
            r"\[\s*(?P<x>-?\d+(?:\.\d+)?)[dDfF]?\s*,\s*"
            r"(?P<y>-?\d+(?:\.\d+)?)[dDfF]?\s*,\s*"
            r"(?P<z>-?\d+(?:\.\d+)?)[dDfF]?\s*\]",
            str(resp),
        )

        if not match:
            return None

        return (
            float(match.group("x")),
            float(match.group("y")),
            float(match.group("z")),
        )

    def get_player_uuid(self, player):
        """
        return the players uuid
        """
        resp = self.command(f"data get entity {player} UUID")
        match = re.search(
            r"\[I;\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]",
            str(resp),
        )

        if not match:
            return None

        a, b, c, d = (int(match.group(i)) & 0xFFFFFFFF for i in range(1, 5))
        return str(uuid.UUID(int=(a << 96) | (b << 64) | (c << 32) | d))


    def get_player_stats(self, player):
        """
        Return the player's stats dict from the world's stats file, or {} if unavailable.
        """
        player_uuid = players.get_uuid(self.server.id, player)

        self.command("save-all flush")  # stats file only updates on save

        stats_dir = self.world_path / "players" / "stats"    # 26.1 and later
        if not stats_dir.is_dir():
            stats_dir = self.world_path / "stats"            # 1.21.11 and earlier

        try:
            data = json.loads((stats_dir / f"{player_uuid}.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

        return data.get("stats", {})

    def get_mobs_killed(self, player, stats=None):
        """
        Return player's total mob kills, or 0 if unavailable.
        """
        if stats is None:
            stats = self.get_player_stats(player)

        return stats.get("minecraft:custom", {}).get("minecraft:mob_kills", 0)

    def get_blocks_mined(self, player, stats=None):
        """
        Return total blocks mined across all block types, or 0 if unavailable.
        """
        if stats is None:
            stats = self.get_player_stats(player)

        return sum(stats.get("minecraft:mined", {}).values())

    def register_player(self, player):
        """
        make sure the player scoreboards or whatever necessary is created when a player is first registered on a server
        """
         # set the death count to 0
        self.command("scoreboard players set %s deaths 0"%player)

        # get and assign uuid to player
        uuid = self.get_player_uuid(player)
        if uuid:
            players.set_uuid(uuid)


    # Process

    def java_command(self):
        return [
            "java",
            f"-Xms{self.config['ram_min']}",
            f"-Xmx{self.config['ram_max']}",
            *JVM_FLAGS,
            "-jar",
            "server.jar",
            "--nogui",
        ]

    def start(self, background=False):
        """
        Apply property overrides and launch the server.

        In the background the server gets its own session and logs
        to console.log; otherwise it uses this terminal. Returns
        the subprocess.Popen.
        """
        if self.is_running():
            raise RuntimeError(f"{self.name} ({self.folder}) is already running.")

        if not self.eula_approved():
            raise RuntimeError(
                f"EULA not accepted for {self.name} ({self.folder}). "
                "Run mc-confirm first."
            )

        self.ensure_rcon()
        self.configure_properties()

        self._log_offset = (
            self.log_path.stat().st_size if self.log_path.is_file() else 0
        )

        if background:
            with self.log_path.open("a") as log:
                process = subprocess.Popen(
                    self.java_command(),
                    cwd=self.path,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        else:
            process = subprocess.Popen(self.java_command(), cwd=self.path)

        self._remember("server", process.pid)
        self.ensure_listener()

        return process

    def wait_until_ready(self, process, timeout=READY_TIMEOUT):
        """
        Wait for a background start() to finish loading, by watching
        console.log for Minecraft's "Done (...)!" line.

        Returns the seconds taken. Raises RuntimeError with the last
        log lines if the server exits first, or on timeout.
        """
        started = time.monotonic()
        offset = self._log_offset

        while time.monotonic() - started < timeout:
            with self.log_path.open("r", errors="replace") as log:
                log.seek(offset)
                new_text = log.read()

            for line in new_text.splitlines():
                if "]: Done (" in line:
                    return time.monotonic() - started

            if process.poll() is not None:
                tail = "\n".join(new_text.strip().splitlines()[-10:])
                self._forget("server")
                raise RuntimeError(
                    f"{self.name} ({self.folder}) exited during startup "
                    f"(code {process.returncode}):\n{tail}"
                )

            time.sleep(1)

        raise RuntimeError(
            f"{self.name} ({self.folder}) did not finish loading within "
            f"{timeout} seconds. It is still running; check console.log."
        )

    def _remember(self, role, pid):
        """Record a process we just started in the servers table."""
        with DatabaseClient() as db:
            registry.set_process(db, self.id, role, pid, psutil.Process(pid).create_time())

    def _forget(self, role):
        with DatabaseClient() as db:
            registry.set_process(db, self.id, role)

    def _tracked_process(self, role, is_ours):
        """
        The live psutil.Process recorded for role ("server" or
        "listener"), or None. A stale record (process gone or PID
        reused) is cleared.
        """
        with DatabaseClient() as db:
            record = registry.get(db, self.id) or {}
        pid = record.get(f"{role}_pid")

        if pid is None:
            return None

        try:
            process = psutil.Process(pid)

            if (
                abs(process.create_time() - record[f"{role}_started"]) > 0.01
                or process.status() == psutil.STATUS_ZOMBIE
                or not is_ours(process)
            ):
                self._forget(role)
                return None

            return process

        except psutil.NoSuchProcess:
            self._forget(role)
            return None

        except (OSError, TypeError, psutil.Error):
            return None

    def get_process(self):
        """The running server's psutil.Process, or None."""
        return self._tracked_process(
            "server",
            lambda process: process.cwd() == str(self.path)
            and "server.jar" in process.cmdline(),
        )

    def is_running(self):
        return self.get_process() is not None

    def uptime(self):
        """Seconds since the server started, or None if not running."""
        process = self.get_process()

        if process is None:
            return None

        return time.time() - process.create_time()

    def stop(self, timeout=60):
        """
        Ask the server to shut down (SIGTERM, which Minecraft treats
        as a clean stop) and wait.

        Returns True if it is no longer running. If it doesn't exit
        within the timeout it is left running and False is returned.

        Once stopped, anyone still marked online in the players table
        is logged out, which also tidies up after a crash.
        """
        process = self.get_process()

        if process is not None:
            process.terminate()

            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                return False

            self._forget("server")

        self.stop_listener()

        with DatabaseClient() as db:
            sessions.recover(db, self.id)

        return True

    # Listener

    def get_listener(self):
        """The running listener's psutil.Process, or None."""
        return self._tracked_process(
            "listener",
            # Listeners started by older code were passed the folder name.
            lambda process: process.cmdline()[1:] in (
                ["-m", LISTENER_MODULE, str(self.id)],
                ["-m", LISTENER_MODULE, self.folder],
                [str(LEGACY_LISTENER), self.folder],
            ),
        )

    def ensure_listener(self):
        """
        Start this server's listener (listener.py) unless it's already
        running. It runs in the background until stop_listener().
        Returns its psutil.Process.
        """
        process = self.get_listener()

        if process is not None:
            return process

        # cwd=ROOT puts the project on the listener's import path for -m.
        with open(self.listener_log_path, "a", buffering=1) as log_fd:
            process = subprocess.Popen(
                [str(VENV_PYTHON), "-m", LISTENER_MODULE, str(self.id)],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log_fd,
                stderr=log_fd,
                start_new_session=True,
            )
        self._remember("listener", process.pid)

        return psutil.Process(process.pid)

    def stop_listener(self, timeout=5):
        """Stop the listener if it's running."""
        process = self.get_listener()

        if process is None:
            return

        process.terminate()

        try:
            process.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)

        self._forget("listener")

    def players(self):
        """
        (online, max, [names]) from the running server, or None if it
        isn't running or RCON can't be reached.
        """
        try:
            reply = self.command("list")
        except RconError:
            return None

        match = _PLAYER_LIST.search(reply)

        if match is None:
            return None

        names = [name.strip() for name in match[3].split(",") if name.strip()]
        return int(match[1]), int(match[2]), names

    def announce(self, message):
        """Say something in game chat. Returns False if RCON isn't reachable."""
        try:
            self.command(f"say {message}")
            return True
        except RconError:
            return False

    def restart(self, warn_seconds=0, reason="restarting"):
        """
        Stop and start again (in the background), waiting until
        loaded. Players get a chat warning first if warn_seconds > 0.
        Returns the seconds the start took.
        """
        if warn_seconds and self.announce(
            f"Server {reason} in {warn_seconds} seconds."
        ):
            time.sleep(warn_seconds)

        if not self.stop():
            raise RuntimeError(
                f"{self.name} ({self.folder}) did not stop; not restarting."
            )

        return self.wait_until_ready(self.start(background=True))

    # Backups

    @property
    def world_path(self):
        return self.path / self.get_property("level-name", "world")

    def backups(self):
        """Backup archives, newest first."""
        return _backup.listing(self)

    def saving_paused(self):
        """See backup.saving_paused()."""
        return _backup.saving_paused(self)

    def backup(self, label=None, prune=True):
        """Archive the world into backups/. Returns (path, paused)."""
        return _backup.create(self, label, prune)

    def prune_backups(self, keep=None):
        """Delete the oldest backups beyond backup_history_size. Returns them."""
        return _backup.prune_old(self, keep)

    def restore(self, backup_path):
        """Replace the world with a backup. The server must be stopped."""
        return _backup.restore(self, backup_path)

    # Maintenance

    def update_size(self):
        """Record server and backup sizes (GB) in config.json."""
        bytes_to_gb = 1024 ** 3

        total = _directory_size(self.path)
        backups = (
            _directory_size(self.backups_path)
            if self.backups_path.is_dir() else 0
        )

        self.config["size"] = round((total - backups) / bytes_to_gb, 1)
        self.config["backup_size"] = round(backups / bytes_to_gb, 1)

        self.save()

    def delete(self):
        """
        Mark the server inactive, hiding it from every script. Its
        folder, world and backups are left on disk.
        """
        if self.is_running():
            raise RuntimeError(f"Stop {self.name} ({self.folder}) before deleting it.")

        self.stop_listener()
        with DatabaseClient() as db:
            registry.set_status(db, self.id, registry.INACTIVE)
        self.record["status"] = registry.INACTIVE

    def update_version(self, version_file, version):
        """
        Replace server.jar. Safe while running; the new version is
        used from the next start.
        """
        version_file = Path(version_file)

        if not version_file.is_file():
            raise FileNotFoundError(f"Version file not found: {version_file}")

        temp_path = self.path / "server.jar.tmp"
        shutil.copy2(version_file, temp_path)
        temp_path.replace(self.path / "server.jar")

        self.config["version"] = version
        self.save()
