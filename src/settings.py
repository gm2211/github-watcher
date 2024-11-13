import os
import traceback
from dataclasses import asdict, dataclass, field
from typing import List
from datetime import datetime

import yaml


@dataclass
class ThresholdPair:
    warning: int
    danger: int


@dataclass
class Thresholds:
    files: ThresholdPair = field(default_factory=lambda: ThresholdPair(10, 50))
    additions: ThresholdPair = field(default_factory=lambda: ThresholdPair(500, 1000))
    deletions: ThresholdPair = field(default_factory=lambda: ThresholdPair(500, 2000))
    age: ThresholdPair = field(default_factory=lambda: ThresholdPair(7, 14))
    recently_closed_days: int = 7


@dataclass
class RefreshInterval:
    value: int = 30
    unit: str = "seconds"

    def to_millis(self) -> int:
        if self.unit == "seconds":
            return self.value * 1000
        elif self.unit == "minutes":
            return self.value * 60 * 1000
        else:  # hours
            return self.value * 60 * 60 * 1000


@dataclass
class Settings:
    users: List[str] = field(default_factory=list)
    refresh: RefreshInterval = field(default_factory=RefreshInterval)
    thresholds: Thresholds = field(default_factory=Thresholds)
    settings_path: str = field(default="")

    @classmethod
    def load(cls, settings_filename: str = "settings.yml") -> "Settings":
        settings_path = os.path.expanduser(
            os.path.join(os.path.dirname(__file__), settings_filename)
        )

        if not os.path.exists(settings_path):
            return cls(settings_path=settings_path)

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Create settings instance with loaded data
            settings = cls(
                users=data.get("users", []),
                refresh=RefreshInterval(**data.get("refresh", {})),
                thresholds=Thresholds(
                    files=ThresholdPair(**data.get("thresholds", {}).get("files", {})),
                    additions=ThresholdPair(
                        **data.get("thresholds", {}).get("additions", {})
                    ),
                    deletions=ThresholdPair(
                        **data.get("thresholds", {}).get("deletions", {})
                    ),
                    age=ThresholdPair(**data.get("thresholds", {}).get("age", {})),
                    recently_closed_days=data.get("thresholds", {}).get(
                        "recently_closed_days", 7
                    ),
                ),
                settings_path=settings_path,
            )
            return settings

        except Exception as e:
            print(f"Error loading settings: {e}")
            traceback.print_exc()
            return cls(settings_path=settings_path)

    def save(self):
        """Save current settings to YAML file"""
        try:
            # Convert dataclass to dict for serialization
            settings_dict = {
                "users": self.users,
                "refresh": asdict(self.refresh),
                "thresholds": {
                    "files": asdict(self.thresholds.files),
                    "additions": asdict(self.thresholds.additions),
                    "deletions": asdict(self.thresholds.deletions),
                    "age": asdict(self.thresholds.age),
                    "recently_closed_days": self.thresholds.recently_closed_days,
                },
            }

            with open(self.settings_path, "w") as f:
                yaml.safe_dump(settings_dict, f, default_flow_style=False)

        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key: str, default=None):
        """Get a setting value by key path (e.g., 'thresholds.files.warning')"""
        try:
            value = self
            for part in key.split("."):
                value = getattr(value, part)
            return value
        except AttributeError:
            return default

    def set(self, key: str, value):
        """Set a setting value by key path"""
        try:
            parts = key.split(".")
            obj = self
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
            self.save()
        except AttributeError as e:
            print(f"Error setting {key}: {e}")
