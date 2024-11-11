import os
from typing import Any, Dict

import yaml

DEFAULT_SETTINGS = {
    "users": [],
    "refresh": {"value": 30, "unit": "seconds"},
    "thresholds": {
        "files": {"warning": 10, "danger": 50},
        "additions": {"warning": 500, "danger": 1000},
        "deletions": {"warning": 2000, "danger": 5000},
        "recently_closed_days": 7,
    },
}


class Settings:
    def __init__(self, settings_path: str, settings: Dict[str, Any]):
        self.settings_path = settings_path
        self._settings = settings

    @staticmethod
    def load(settings_filename: str = "settings.yml") -> "Settings":
        os.path.expanduser(os.path.join(os.path.dirname(__file__), settings_filename))
        settings = Settings(settings_filename, DEFAULT_SETTINGS.copy())

        if not os.path.exists(settings.settings_path):
            return settings

        try:
            with open(settings.settings_path, "r") as f:
                loaded_settings = yaml.safe_load(f) or {}
                merged = {**DEFAULT_SETTINGS, **loaded_settings}
                settings._settings = merged
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return settings

    def save(self):
        """Save current settings to YAML file"""
        try:
            with open(self.settings_path, "w") as f:
                yaml.dump(self._settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value"""
        self._settings[key] = value
        self.save()

    def update(self, new_settings: Dict[str, Any]):
        """Update multiple settings at once"""
        self._settings.update(new_settings)
        self.save()

    @property
    def all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._settings.copy()
