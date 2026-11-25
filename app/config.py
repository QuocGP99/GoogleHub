"""Application configuration constants for Google Hub."""

import os
import sys

# Account profile configurations (add or edit profiles here)
ACCOUNT_PROFILES = [
    {"id": "personal", "name": "👤 Cá nhân", "color": "#3B82F6"},
    {"id": "studio",   "name": "📸 GP Studio99", "color": "#10B981"},
    {"id": "work",     "name": "💻 Dự án / Dev", "color": "#8B5CF6"},
]

# List of 12 Google Web services
GOOGLE_SERVICES = [
    ("Gemini", "https://gemini.google.com"),
    ("Gmail", "https://mail.google.com"),
    ("Drive", "https://drive.google.com"),
    ("YouTube", "https://www.youtube.com"),
    ("Photos", "https://photos.google.com"),
    ("Maps", "https://www.google.com/maps"),
    ("Dịch", "https://translate.google.com"),
    ("Docs", "https://docs.google.com/document"),
    ("Sheets", "https://docs.google.com/spreadsheets"),
    ("Slides", "https://docs.google.com/presentation"),
    ("Calendar", "https://calendar.google.com"),
    ("Meet", "https://meet.google.com"),
]

# Tabs exempt from hibernation to avoid interrupting calls or background audio
NEVER_FREEZE_TABS = {"Meet", "YouTube"}

# Idle timeout before auto-freezing unused tabs (15 minutes)
IDLE_TIMEOUT_SECONDS = 15 * 60

# Firefox User-Agent to avoid Google's "This browser or app may not be secure" block
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
    "Gecko/20100101 Firefox/133.0"
)

# Chromium flags passed before QApplication initialization
CHROMIUM_FLAGS = (
    "--disable-blink-features=AutomationControlled "
    "--enable-webgl "
    "--ignore-gpu-blocklist"
)


def get_app_data_root():
    """Return a writable root directory for persistent app data and settings."""
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local_app_data, "GoogleHub")
    return os.getcwd()


def get_profiles_root():
    """Return a writable base directory for per-account profile storage."""
    return os.path.join(get_app_data_root(), "google_hub_profiles")
