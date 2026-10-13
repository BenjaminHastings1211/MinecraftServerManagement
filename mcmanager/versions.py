"""Minecraft server versions: Mojang's manifest and the local VERSIONS folder."""

import json
import urllib.request

from pathlib import Path

from mcmanager.paths import VERSIONS


MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def version_to_filename(version):
    return f"server-{version.replace('.', '-')}.jar"


def filename_to_version(path):
    return Path(path).stem.removeprefix("server-").replace("-", ".")


def version_key(version):
    """Sortable key for "26.3" / "1.21.10" style versions."""
    return [int(part) if part.isdigit() else -1 for part in str(version).split(".")]


def find_version_jar(version=None):
    """
    Return the JAR in VERSIONS for a version number ("26.3") or
    filename ("server-26-3.jar"), or the newest version if None.
    """
    if version is None:
        jars = list(VERSIONS.glob("server-*.jar"))

        if not jars:
            raise FileNotFoundError("No server versions found.")

        return max(jars, key=lambda jar: version_key(filename_to_version(jar)))

    filename = version if version.endswith(".jar") else version_to_filename(version)
    jar = VERSIONS / filename

    if not jar.is_file():
        raise FileNotFoundError(f"Version not found: {filename}")

    return jar


def _fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def _manifest():
    return _fetch_json(MANIFEST_URL)


def latest_release():
    """The newest release version number from Mojang, e.g. "26.3"."""
    return _manifest()["latest"]["release"]


def download(version):
    """
    Return the local JAR for a version, downloading it from Mojang
    first if needed.
    """
    jar = VERSIONS / version_to_filename(version)

    if jar.is_file():
        return jar

    for entry in _manifest()["versions"]:
        if entry["id"] == version:
            break
    else:
        raise ValueError(f"Minecraft version not found: {version}")

    url = _fetch_json(entry["url"])["downloads"]["server"]["url"]

    VERSIONS.mkdir(exist_ok=True)
    partial = jar.with_name(jar.name + ".partial")

    try:
        urllib.request.urlretrieve(url, partial)
        partial.replace(jar)
    finally:
        partial.unlink(missing_ok=True)

    return jar
