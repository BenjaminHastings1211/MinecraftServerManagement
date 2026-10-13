"""
Imported first by every script. Re-runs the script with the project's
.venv Python if it was started with another one (e.g. the system
python3 from the #! line), then puts the project root on the import
path so `import mcmanager` works from any directory or symlink.
"""

import os
import sys

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "bin" / "python"

if (
    VENV_PYTHON.is_file()
    and Path(sys.prefix).resolve() != VENV.resolve()
    and not os.environ.get("MCMANAGER_BOOTSTRAPPED")
):
    os.environ["MCMANAGER_BOOTSTRAPPED"] = "1"
    os.execv(VENV_PYTHON, [str(VENV_PYTHON), sys.argv[0], *sys.argv[1:]])

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
