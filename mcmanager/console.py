"""
Two-way link to a running server, for mc-cmd and your own scripts.

Commands go over RCON; output is read live from logs/latest.log.

    from mcmanager.server import Server

    with Server(2).console() as console:
        print(console.command("list"))

        for line in console.lines():          # blocks, yields new lines
            print(line.message)

Console is thread-safe: one thread can read lines() while others
send commands.
"""

import re
import threading
import time

from dataclasses import dataclass

from mcmanager.rcon import RconError


# Minecraft formatting codes, e.g. §a (green) or §l (bold).
FORMATTING = re.compile("§[0-9a-fk-or]", re.IGNORECASE)

_LOG_LINE = re.compile(
    r"^\[(?P<time>[\d:]+)\] \[(?P<source>[^\]]+)/(?P<level>[A-Z]+)\]: (?P<message>.*)$"
)


def strip_formatting(text):
    return FORMATTING.sub("", text)


@dataclass(frozen=True)
class LogLine:
    """One line of server output. Unparseable lines (e.g. stack traces)
    have only raw and message set."""

    raw: str
    message: str
    time: str = None
    source: str = None
    level: str = None

    @classmethod
    def parse(cls, raw):
        raw = raw.rstrip("\n")
        match = _LOG_LINE.match(raw)

        if match is None:
            return cls(raw=raw, message=raw)

        return cls(raw=raw, **match.groupdict())

    def __str__(self):
        return self.raw


class LogFollower:
    """Reads lines appended to a log file, surviving log rotation."""

    def __init__(self, path, from_start=False):
        self.path = path
        self._file = None
        self._inode = None
        self._buffer = ""
        self._from_start = from_start

    def _open(self):
        try:
            file = self.path.open("r", encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return False

        if self._file is not None:
            self._file.close()

        self._file = file
        self._inode = self.path.stat().st_ino
        self._buffer = ""

        if not self._from_start:
            file.seek(0, 2)

        # After a rotation the new file is read from the beginning.
        self._from_start = True
        return True

    def read(self):
        """Complete new lines since the last call (possibly empty)."""
        if self._file is None and not self._open():
            return []

        try:
            stat = self.path.stat()
            rotated = stat.st_ino != self._inode or stat.st_size < self._file.tell()
        except FileNotFoundError:
            rotated = False

        lines = self._drain()

        if rotated and self._open():
            lines += self._drain()

        return lines

    def _drain(self):
        self._buffer += self._file.read()
        *lines, self._buffer = self._buffer.split("\n")
        return lines

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None


class Console:
    def __init__(self, server, poll_interval=0.25):
        self.server = server
        self.poll_interval = poll_interval
        self._rcon = None
        self._lock = threading.Lock()
        self._log = LogFollower(server.path / "logs" / "latest.log")

    def open(self):
        self._rcon = self.server.rcon()
        self._rcon.connect()
        self._log.read()  # Start following from the current end.
        return self

    def close(self):
        if self._rcon is not None:
            self._rcon.close()
            self._rcon = None

        self._log.close()

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def command(self, command):
        """Run a command (no leading /) and return its reply."""
        if self._rcon is None:
            raise RconError("Console is not open.")

        with self._lock:
            reply = self._rcon.command(command.strip().removeprefix("/"))

        return strip_formatting(reply).strip()

    def poll(self):
        """New output lines since the last poll, without waiting."""
        return [LogLine.parse(line) for line in self._log.read()]

    def lines(self, stop=None):
        """
        Yield output lines as they appear, forever, or until the
        threading.Event `stop` is set.
        """
        while stop is None or not stop.is_set():
            new_lines = self.poll()

            if not new_lines:
                time.sleep(self.poll_interval)

            yield from new_lines

    def wait_for(self, pattern, timeout=None):
        """
        Wait for an output line whose message matches the regex
        `pattern` (or a function LogLine -> bool). Returns the line,
        or None on timeout.
        """
        if isinstance(pattern, str):
            regex = re.compile(pattern)
            matches = lambda line: regex.search(line.message)
        else:
            matches = pattern

        deadline = None if timeout is None else time.monotonic() + timeout

        while deadline is None or time.monotonic() < deadline:
            for line in self.poll():
                if matches(line):
                    return line

            time.sleep(self.poll_interval)

        return None
