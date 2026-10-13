#!/usr/bin/env python3
"""mc-monitor: live dashboard of a server and the Raspberry Pi's health."""

import _bootstrap  # noqa: F401  (must come first; see _bootstrap.py)

import select
import shutil
import subprocess
import sys
import termios
import time
import tty

from contextlib import contextmanager
from datetime import datetime

import psutil

from mcmanager import cli


REFRESH_INTERVAL = 1
SLOW_CHECK_INTERVAL = 5  # throttling and players
CLEAR_SCREEN = "\033[H\033[J"


def read_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as file:
            return int(file.read().strip()) / 1000
    except (OSError, ValueError):
        return None


def read_throttling():
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        flags = int(result.stdout.strip().split("=")[-1], 16)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None

    return {
        "raw": hex(flags),
        "undervoltage": bool(flags & 0x1),
        "throttled": bool(flags & 0x4),
        "undervoltage_history": bool(flags & 0x10000),
        "throttled_history": bool(flags & 0x40000),
    }


@contextmanager
def keypress_mode():
    """Read single keys without Enter (no-op when not in a terminal)."""
    if not sys.stdin.isatty():
        yield
        return

    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        yield
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def quit_pressed():
    if not sys.stdin.isatty():
        return False

    readable, _, _ = select.select([sys.stdin], [], [], 0)
    return bool(readable) and sys.stdin.read(1).lower() == "q"


def flag(value):
    return cli.red("YES") if value else "No"


def render(server, process, monitor_start, cpu_percent, throttling, players):
    """The dashboard as a list of lines."""
    memory = process.memory_info()
    system_memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    temperature = read_cpu_temperature()
    now = datetime.now().astimezone()

    if players is None:
        players_text = "Unknown (RCON not reachable)"
    else:
        online, maximum, names = players
        players_text = f"{online}/{maximum}" + (f"  {', '.join(names)}" if names else "")

    lines = [
        "=" * 62,
        "              MINECRAFT SERVER MONITOR",
        "=" * 62,
        f"Updated:          {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"Server:           {cli.server_label(server)}",
        f"PID:              {process.pid}",
        f"Process status:   {process.status()}",
        f"Monitor uptime:   {cli.format_duration(time.time() - monitor_start, precise=True)}",
        f"Server uptime:    {cli.format_duration(time.time() - process.create_time(), precise=True)}",
        f"Players:          {players_text}",
        "",
        "--- MINECRAFT JAVA PROCESS ---",
        f"CPU usage:        {cpu_percent:.1f}%",
        f"Physical RAM:     {cli.format_bytes(memory.rss)} "
        f"({memory.rss / system_memory.total * 100:.1f}% of Pi RAM)",
        f"Virtual memory:   {cli.format_bytes(memory.vms)}",
        f"Threads:          {process.num_threads()}",
        f"Configured RAM:   {server.config.get('ram_min', '?')} - {server.config.get('ram_max', '?')}",
        "",
        "--- RASPBERRY PI ---",
        f"System RAM:       {cli.format_bytes(system_memory.used)} / "
        f"{cli.format_bytes(system_memory.total)} ({system_memory.percent:.1f}%)",
        f"Available RAM:    {cli.format_bytes(system_memory.available)}",
        "CPU temperature:  "
        + ("Unavailable" if temperature is None else f"{temperature:.1f} °C"),
        f"Root disk:        {cli.format_bytes(disk.used)} / {cli.format_bytes(disk.total)} "
        f"({disk.used / disk.total * 100:.1f}%)",
        f"Disk free:        {cli.format_bytes(disk.free)}",
        "",
        "--- PI THROTTLING ---",
    ]

    if throttling is None:
        lines.append("Throttle status:  Unavailable")
    else:
        lines += [
            f"Throttle flags:        {throttling['raw']}",
            f"Undervoltage now:      {flag(throttling['undervoltage'])}",
            f"Throttling now:        {flag(throttling['throttled'])}",
            f"Undervoltage history:  {flag(throttling['undervoltage_history'])}",
            f"Throttle history:      {flag(throttling['throttled_history'])}",
        ]

    lines += ["", "Press q to quit."]
    return lines


def monitor(server, process):
    monitor_start = time.time()
    last_slow_check = 0
    throttling = players = None

    process.cpu_percent(interval=None)  # Prime the CPU counter.

    with keypress_mode():
        while not quit_pressed():
            if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                print(f"\n{cli.server_label(server)} stopped.")
                return

            if time.monotonic() - last_slow_check >= SLOW_CHECK_INTERVAL:
                throttling = read_throttling()
                players = server.players()
                last_slow_check = time.monotonic()

            lines = render(
                server,
                process,
                monitor_start,
                process.cpu_percent(interval=None),
                throttling,
                players,
            )
            print(CLEAR_SCREEN + "\n".join(lines), flush=True)

            time.sleep(REFRESH_INTERVAL)


def main():
    parser = cli.parser(
        "Live dashboard of a running server and the Raspberry Pi's health.",
        target=cli.ONE,
    )
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)
    process = server.get_process()

    if process is None:
        raise cli.CommandError(f"{cli.server_label(server)} is not running.")

    try:
        monitor(server, process)
    except psutil.NoSuchProcess:
        print(f"\n{cli.server_label(server)} stopped.")


if __name__ == "__main__":
    cli.run(main)
