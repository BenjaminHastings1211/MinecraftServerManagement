from pathlib import Path


def _unescape(text):
    """Decode Java .properties escapes, e.g. minecraft\\:normal or \\u00A7."""
    result = []
    i = 0

    while i < len(text):
        char = text[i]

        if char != "\\" or i + 1 == len(text):
            result.append(char)
            i += 1
            continue

        following = text[i + 1]

        if following == "u" and i + 6 <= len(text):
            try:
                result.append(chr(int(text[i + 2:i + 6], 16)))
                i += 6
                continue
            except ValueError:
                pass

        result.append(
            {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}.get(following, following)
        )
        i += 2

    return "".join(result)


def _escape(text):
    """Encode a value so Java reads it back exactly (non-ASCII as \\uXXXX)."""
    result = []

    for char in text:
        if char == "\\":
            result.append("\\\\")
        elif char == "\n":
            result.append("\\n")
        elif ord(char) > 0x7E:
            result.append(f"\\u{ord(char):04X}")
        else:
            result.append(char)

    escaped = "".join(result)

    # A leading space would otherwise be stripped by Java.
    if escaped.startswith(" "):
        escaped = "\\" + escaped

    return escaped


def format_value(value):
    """Convert a Python value to its server.properties form."""
    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


class Properties:
    """
    Reads and edits a Minecraft server.properties file.

    Comments, ordering and untouched lines are preserved on save.
    Only keys that already exist in the file can be set, since
    Minecraft writes every valid key on first run - an unknown key
    is almost always a typo.

        with Properties(path) as properties:
            properties["server-port"] = 25566
    """

    def __init__(self, path):
        self.path = Path(path)
        self.properties = {}
        self.modified = {}

        self._load()

    def _load(self):
        if not self.path.is_file():
            raise FileNotFoundError(
                f"Properties file not found: {self.path}"
            )

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                key, value = self._parse(line)

                if key is not None:
                    self.properties[key] = value

    @staticmethod
    def _parse(line):
        """Return (key, value) for a property line, or (None, None)."""
        line = line.strip()

        if not line or line[0] in "#!" or "=" not in line:
            return None, None

        key, value = line.split("=", 1)

        return key.strip(), _unescape(value)

    def __contains__(self, key):
        return key in self.properties

    def __getitem__(self, key):
        return self.modified.get(key, self.properties[key])

    def __setitem__(self, key, value):
        if key not in self.properties:
            raise KeyError(f"Unknown server property: {key}")

        self.modified[key] = format_value(value)

    def get(self, key, default=None):
        return self[key] if key in self else default

    def keys(self):
        return self.properties.keys()

    def update(self, properties):
        """
        Set several properties at once.

        Returns the keys that were skipped because they don't exist
        in the file.
        """
        unknown = []

        for key, value in properties.items():
            try:
                self[key] = value
            except KeyError:
                unknown.append(key)

        return unknown

    def save(self):
        """Write modified values back to the file."""
        changed = {
            key: value
            for key, value in self.modified.items()
            if value != self.properties[key]
        }

        if not changed:
            return

        lines = []

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                key, _ = self._parse(line)

                if key in changed:
                    line = f"{key}={_escape(changed[key])}\n"

                lines.append(line)

        temp_path = self.path.with_name(self.path.name + ".tmp")
        temp_path.write_text("".join(lines), encoding="utf-8")
        temp_path.replace(self.path)

        self.properties.update(changed)
        self.modified.clear()

    def close(self):
        self.save()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.save()
