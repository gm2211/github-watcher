import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from github_pr_watcher.objects import PullRequest
from github_pr_watcher.utils import flatten


class SectionName(Enum):
    """Enum for section names to ensure type safety"""

    NEEDS_REVIEW = "Needs Review"
    CHANGES_REQUESTED = "Changes Requested"
    OPEN_PRS = "Open PRs"
    RECENTLY_CLOSED = "Recently Closed"


@dataclass
class SectionData:
    """Data for a section including PRs and timestamp"""

    prs_by_author: Dict[str, list[PullRequest]]
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "prs_by_author": {
                user: [pr.to_dict() for pr in prs]
                for user, prs in self.prs_by_author.items()
            },
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SectionData":
        return cls(
            prs_by_author={
                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                for user, prs in data["prs_by_author"].items()
            },
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class UIState:
    """Main UI state class"""

    state_file: Path
    is_expanded_by_section: Dict[SectionName, bool] = field(
        default_factory=lambda: {name: True for name in SectionName}
    )
    data_by_section: Dict[SectionName, Optional[SectionData]] = field(
        default_factory=lambda: {name: None for name in SectionName}
    )

    def get_section_expanded(self, section_name: SectionName) -> bool:
        """Get expansion state for a section"""
        return self.is_expanded_by_section.get(section_name, True)

    def set_section_expanded(self, section_name: SectionName, expanded: bool) -> None:
        """Set expansion state for a section"""
        self.is_expanded_by_section[section_name] = expanded
        self.save()

    def get_pr_data(
        self, section_name: SectionName
    ) -> tuple[Dict[str, list[PullRequest]], Optional[str]]:
        """Get PR data and timestamp for a section"""
        try:
            section_data = self.data_by_section.get(section_name)
            if section_data:
                return section_data.prs_by_author, section_data.timestamp.isoformat()
        except ValueError:
            pass
        return {}, None

    def update_pr_data(
        self,
        section_name: SectionName,
        prs_by_author: Dict[str, List[Tuple[PullRequest, bool]]],
    ) -> None:
        """Update PR data for a section"""
        try:
            existing: List[PullRequest] = (
                flatten(
                    list(self.data_by_section.get(section_name).prs_by_author.values())
                )
                if self.data_by_section.get(section_name)
                else []
            )
            merged = {}

            for user, prs in prs_by_author.items():
                for pr, partial in prs:
                    if partial:
                        existing_pr = next(pr.number == ex.number for ex in existing)
                        merged.setdefault(user, []).append(existing_pr)
                    else:
                        merged.setdefault(user, []).append(pr)

            # Merge prs_by_author with existing data, if partial boolean is true, don't overwrite existing PRs
            self.data_by_section[section_name] = SectionData(
                prs_by_author=merged, timestamp=datetime.now()
            )
            self.save()
        except ValueError:
            pass

    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization"""
        return {
            "is_expanded_by_section": {
                section.name: expanded
                for section, expanded in self.is_expanded_by_section.items()
            },
            "data_by_section": {
                section.name: data.to_dict() if data else None
                for section, data in self.data_by_section.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, state_file: Path) -> "UIState":
        """Create state from dictionary"""
        # Initialize with default values for all sections
        is_expanded_by_section = {name: True for name in SectionName}
        data_by_section = {name: None for name in SectionName}

        # Update with any saved values
        if saved_expanded := data.get("is_expanded_by_section"):
            for section_name, expanded in saved_expanded.items():
                try:
                    section = SectionName[section_name]
                    is_expanded_by_section[section] = expanded
                except (KeyError, ValueError):
                    continue

        if saved_data := data.get("data_by_section"):
            for section_name, section_data in saved_data.items():
                try:
                    section = SectionName[section_name]
                    data_by_section[section] = (
                        SectionData.from_dict(section_data) if section_data else None
                    )
                except (KeyError, ValueError):
                    continue

        return cls(
            state_file=state_file,
            is_expanded_by_section=is_expanded_by_section,
            data_by_section=data_by_section,
        )

    @staticmethod
    def load(state_file: str = "state.json") -> "UIState":
        """Load UI state from file"""
        state_path = Path(__file__).parent / state_file

        if not state_path.exists():
            return UIState(state_file=state_path)

        try:
            with open(state_path, "r") as f:
                data = json.load(f)
            return UIState.from_dict(data, state_path)
        except Exception as e:
            print(f"Error loading UI state: {e}")
            traceback.print_exc()
            return UIState(state_file=state_path)

    def save(self) -> None:
        """Save UI state to file"""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving UI state: {e}")
            traceback.print_exc()
