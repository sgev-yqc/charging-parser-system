"""Runtime configuration for the charging parser application."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG_FILE = PROJECT_ROOT / "config.local.json"


def _read_local_config():
    """Read the optional local config file, or return an empty mapping."""
    if not LOCAL_CONFIG_FILE.exists():
        return {}
    with LOCAL_CONFIG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _resolve_data_dir(configured):
    """Resolve a configured path, anchoring relative paths at the project root."""
    path = Path(configured).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_data_dir():
    """Return the configured data directory, defaulting to ./data in the project."""
    configured = _read_local_config().get("data_dir")
    if configured:
        return _resolve_data_dir(configured)
    return PROJECT_ROOT / "data"
