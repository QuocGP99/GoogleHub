"""Persistent JSON settings manager for Google Hub."""

import copy
import json
import os

from app.config import ACCOUNT_PROFILES, get_app_data_root

DEFAULT_SETTINGS = {
    "language": "vi",
    "idle_timeout_minutes": 15,
    "minimize_to_tray": True,
    "profiles": copy.deepcopy(ACCOUNT_PROFILES),
}


def get_settings_path():
    """Return the path to the persistent settings.json file."""
    root = get_app_data_root()
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "settings.json")


def load_settings():
    """Load settings from disk, falling back to defaults for missing keys."""
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    path = get_settings_path()
    if not os.path.exists(path):
        return settings

    try:
        with open(path, "r", encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            if stored.get("language") in ("vi", "en"):
                settings["language"] = stored["language"]
            if isinstance(stored.get("idle_timeout_minutes"), int):
                settings["idle_timeout_minutes"] = stored["idle_timeout_minutes"]
            if isinstance(stored.get("minimize_to_tray"), bool):
                settings["minimize_to_tray"] = stored["minimize_to_tray"]
            profiles = stored.get("profiles")
            if isinstance(profiles, list) and len(profiles) > 0:
                valid = [
                    p for p in profiles
                    if isinstance(p, dict) and p.get("id") and p.get("name")
                ]
                if valid:
                    for p in valid:
                        p.setdefault("color", "#0A84FF")
                    settings["profiles"] = valid
    except Exception as e:
        print(f"Error loading settings: {e}")

    return settings


def save_settings(settings):
    """Persist settings dictionary to settings.json."""
    path = get_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
