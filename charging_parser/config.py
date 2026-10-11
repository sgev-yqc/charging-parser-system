"""Runtime configuration for the charging parser application."""

import os
from pathlib import Path


def get_data_dir():
    """Return the configured data directory, with a user-writable default."""
    configured = os.environ.get("CHARGING_PARSER_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "share" / "charging-parser-system"
