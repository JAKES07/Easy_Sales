# ============================================================
# EASY SALES - PERSISTENT DATA LOCATION
# ============================================================
#
# Local development:
#   Uses ./database next to the application.
#
# Render production:
#   Set EASY_SALES_DATA_DIR=/var/data and mount a Render
#   Persistent Disk at /var/data.
#
# All Easy Sales databases MUST use this module so application
# deployments replace code only and do not replace customer data.
# ============================================================

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(
    os.environ.get(
        "EASY_SALES_DATA_DIR",
        str(BASE_DIR / "database")
    )
).expanduser().resolve()

DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_data_path(*parts):
    """Return a path inside Easy Sales' persistent data directory."""
    path = DATA_DIR.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
