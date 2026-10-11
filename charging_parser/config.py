"""Runtime configuration for the charging parser application."""

import json
import os
from pathlib import Path

LOCAL_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.local.json"


def _read_local_config():
    """Read the optional local config file, or return an empty mapping."""
    if not LOCAL_CONFIG_FILE.exists():
        return {}
    with LOCAL_CONFIG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_data_dir():
    """Return the configured data directory, with a user-writable default."""
    configured = os.environ.get("CHARGING_PARSER_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    configured = _read_local_config().get("data_dir")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "share" / "charging-parser-system"
