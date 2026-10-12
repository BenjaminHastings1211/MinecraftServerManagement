"""Minecraft server versions: Mojang's manifest and the local VERSIONS folder."""

import json
import urllib.request

from resources import server as _server
from resources.server import version_key  # noqa: F401  (re-exported)


MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


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
    jar = _server.VERSIONS / _server.version_to_filename(version)

    if jar.is_file():
        return jar

    for entry in _manifest()["versions"]:
        if entry["id"] == version:
            break
    else:
        raise ValueError(f"Minecraft version not found: {version}")

    url = _fetch_json(entry["url"])["downloads"]["server"]["url"]

    _server.VERSIONS.mkdir(exist_ok=True)
    partial = jar.with_name(jar.name + ".partial")

    try:
        urllib.request.urlretrieve(url, partial)
        partial.replace(jar)
    finally:
        partial.unlink(missing_ok=True)

    return jar
