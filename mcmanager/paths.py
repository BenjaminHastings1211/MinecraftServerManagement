"""Project locations, worked out from where this file lives."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SERVERS = ROOT / "servers"
VERSIONS = ROOT / "versions"
DEFAULTS = ROOT / "mcmanager" / "misc" / "defaults.json"
ENV_FILE = ROOT / ".env"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
