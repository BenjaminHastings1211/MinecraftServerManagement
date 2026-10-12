"""
Minimal Minecraft RCON client.

    with Rcon("127.0.0.1", 25575, "secret") as rcon:
        print(rcon.command("list"))

Minecraft collects every RCON client's command output in one shared
buffer, so commands that overlap get each other's replies (or none).
Give every client of a server the same lock_path and their commands
take turns, across threads and processes.
"""

import fcntl
import itertools
import socket
import struct

from contextlib import contextmanager


LOGIN = 3
COMMAND = 2
RESPONSE = 0

# Sent after a command; the server answers it only once the command's
# (possibly multi-packet) response is complete.
_END_MARKER = 100


class RconError(RuntimeError):
    pass


class Rcon:
    def __init__(self, host, port, password, timeout=5, lock_path=None):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.lock_path = lock_path
        self._socket = None
        self._ids = itertools.count(1)

    def connect(self):
        try:
            self._socket = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
        except OSError as error:
            raise RconError(
                f"Cannot connect to RCON on port {self.port} ({error}). "
                "Is the server fully started, and has it been restarted "
                "since RCON was enabled?"
            ) from None

        request_id = self._send(LOGIN, self.password)
        response_id, _, _ = self._receive()

        if response_id == -1 or response_id != request_id:
            self.close()
            raise RconError("RCON login failed: wrong password.")

    def command(self, command):
        """Run a server command and return its output."""
        if self._socket is None:
            raise RconError("Not connected.")

        with self._exclusive():
            request_id = self._send(COMMAND, command)
            end_id = self._send(_END_MARKER, "")
            parts = []

            while True:
                response_id, _, payload = self._receive()

                if response_id == end_id:
                    return "".join(parts)

                if response_id == request_id:
                    parts.append(payload)

    @contextmanager
    def _exclusive(self):
        """Hold lock_path for the duration, if one was given."""
        if self.lock_path is None:
            yield
            return

        # Each call opens its own file, so threads also wait for each other.
        with open(self.lock_path, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def _send(self, packet_type, payload):
        request_id = next(self._ids)
        body = (
            struct.pack("<ii", request_id, packet_type)
            + payload.encode("utf-8")
            + b"\x00\x00"
        )
        self._socket.sendall(struct.pack("<i", len(body)) + body)
        return request_id

    def _receive(self):
        (length,) = struct.unpack("<i", self._read(4))
        data = self._read(length)
        request_id, packet_type = struct.unpack("<ii", data[:8])
        payload = data[8:-2].decode("utf-8", errors="replace")
        return request_id, packet_type, payload

    def _read(self, size):
        data = b""

        try:
            while len(data) < size:
                chunk = self._socket.recv(size - len(data))

                if not chunk:
                    raise RconError("RCON connection closed by server.")

                data += chunk
        except socket.timeout:
            raise RconError("RCON timed out waiting for a response.") from None

        return data
