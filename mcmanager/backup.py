"""
World backups for a Server: archive, list, prune and restore.

Server.backup(), backups(), prune_backups(), restore() and
saving_paused() call these; use those from scripts.
"""

import shutil
import tarfile
import time

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from mcmanager.rcon import RconError


BACKUP_PATTERN = "world-*.tar.gz"


def listing(server):
    """Backup archives, newest first."""
    if not server.backups_path.is_dir():
        return []

    return sorted(
        server.backups_path.glob(BACKUP_PATTERN),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


@contextmanager
def saving_paused(server):
    """
    While inside, a running server has flushed everything to disk
    and won't write to the world, so its files can be copied
    safely. Yields True if paused (or not running), False if the
    server is running but RCON can't be reached.
    """
    if not server.is_running():
        yield True
        return

    try:
        server.command("save-off")
        server.command("save-all flush")
    except RconError:
        yield False
        return

    try:
        yield True
    finally:
        for attempt in range(3):
            try:
                server.command("save-on")
                break
            except RconError:
                time.sleep(2)
        else:
            raise RuntimeError(
                f"Could not turn saving back on for {server.id}! "
                f"Run: mc-cmd {server.id} save-on"
            )


def create(server, label=None, prune=True):
    """
    Archive the world into backups/. Returns (path, paused) where
    paused says whether saving was paused, i.e. the copy is
    guaranteed consistent.
    """
    world = server.world_path

    if not world.is_dir():
        raise FileNotFoundError(f"No world folder found: {world}")

    server.backups_path.mkdir(exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    name = f"world-{stamp}-{label}.tar.gz" if label else f"world-{stamp}.tar.gz"
    path = server.backups_path / name
    partial = path.with_name(name + ".partial")

    try:
        with saving_paused(server) as paused:
            with tarfile.open(partial, "w:gz", compresslevel=6) as tar:
                tar.add(world, arcname=world.name)

        partial.replace(path)

    finally:
        partial.unlink(missing_ok=True)

    if prune:
        prune_old(server)

    return path, paused


def prune_old(server, keep=None):
    """Delete the oldest backups beyond backup_history_size. Returns them."""
    keep = keep or server.config.get("backup_history_size", 5)
    removed = listing(server)[keep:]

    for path in removed:
        path.unlink()

    return removed


def restore(server, backup_path):
    """
    Replace the world with a backup. The server must be stopped;
    the current world is discarded, so back it up first.
    """
    backup_path = Path(backup_path)

    if server.is_running():
        raise RuntimeError(f"Stop {server.name} ({server.id}) before restoring.")

    staging = server.path / ".restore"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            members = tar.getmembers()

            for member in members:
                parts = Path(member.name).parts

                if (
                    member.name.startswith("/")
                    or ".." in parts
                    or not (member.isfile() or member.isdir())
                ):
                    raise ValueError(f"Unsafe entry in backup: {member.name}")

            tar.extractall(staging, members=members)

        extracted = [path for path in staging.iterdir() if path.is_dir()]

        if len(extracted) != 1:
            raise ValueError(f"Backup does not contain a single world folder: {backup_path.name}")

        world = server.world_path
        old_world = world.with_name(world.name + ".old")
        shutil.rmtree(old_world, ignore_errors=True)

        if world.exists():
            world.rename(old_world)

        try:
            extracted[0].rename(world)
        except OSError:
            if old_world.exists():
                old_world.rename(world)
            raise

        shutil.rmtree(old_world, ignore_errors=True)

    finally:
        shutil.rmtree(staging, ignore_errors=True)
