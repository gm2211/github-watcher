import os
import yaml
from typing import Dict, Any

DEFAULT_SETTINGS = {
    "users": [],
    "refresh": {
        "value": 30,
        "unit": "seconds"
    },
    "thresholds": {
        "files": {
            "warning": 10,
            "danger": 50
        },
        "lines": {
            "warning": 500,
            "danger": 1000
        },
        "recently_closed_days": 7
    }
}

class Settings:
    def __init__(self, settings_file: str = "~/.github-pr-watcher.yml"):
        self.settings_file = os.path.expanduser(settings_file)
        self._settings = self.load()

    def load(self) -> Dict[str, Any]:
        """Load settings from YAML file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    loaded_settings = yaml.safe_load(f) or {}
                    # Merge with defaults to ensure all required settings exist
                    return {**DEFAULT_SETTINGS, **loaded_settings}
            except Exception as e:
                print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def save(self):
        """Save current settings to YAML file"""
        try:
            with open(self.settings_file, "w") as f:
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

# Global settings instance
_settings = None

def get_settings():
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings