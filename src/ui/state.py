import json
import os
import traceback
from datetime import datetime
from typing import Any, Dict

from src.objects import PullRequest


class UIState:
    def __init__(self, state_file: str, state=None):
        if state is None:
            state = {}
        self.state_file = state_file
        self.settings: Dict[str, Any] = state

    @staticmethod
    def load(state_file: str = "state.json") -> "UIState":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(script_dir, state_file)
        state = UIState(state_file)

        if not os.path.exists(state_file):
            print(f"Warning: State file not found: {state_file}")
            return UIState(state_file)

        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                # Convert stored PR data back to PullRequest objects
                for section in ["open", "review", "attention", "closed"]:
                    if section in data:
                        section_data = data[section]
                        if isinstance(section_data, dict) and "data" in section_data:
                            section_data["data"] = {
                                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                                for user, prs in section_data["data"].items()
                            }
                state.settings = data
                return state
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
            traceback.print_exc()
            return state

    def save(self):
        """Save current state to file"""
        try:
            print(f"\nDebug - Saving state to {self.state_file}")
            print(f"Debug - Current state: {self.settings}")

            # Create a copy of state for serialization
            serializable_state = {}
            for key, value in self.settings.items():
                if key.endswith("_expanded"):  # UI state
                    serializable_state[key] = value
                elif isinstance(value, dict) and "data" in value:  # PR data
                    serializable_state[key] = {
                        "timestamp": value["timestamp"],
                        "data": {
                            user: [pr.to_dict() for pr in prs]
                            for user, prs in value["data"].items()
                        },
                    }
                else:
                    serializable_state[key] = value

            print(f"Debug - Serializable state: {serializable_state}")

            with open(self.state_file, "w") as f:
                json.dump(serializable_state, f, indent=2)
            print("Debug - State saved successfully")

        except Exception as e:
            print(f"Warning: Failed to save state: {e}")
            import traceback

            traceback.print_exc()

    def update_pr_data(self, section: str, data: dict):
        """Update PR data for a section"""
        self.settings[section] = {"data": data, "timestamp": datetime.now().isoformat()}
        self.save()

    def get_pr_data(
        self, section: str
    ) -> tuple[Any, Any] | tuple[dict[Any, Any], None]:
        """Get PR data and timestamp for a section"""
        if section in self.settings:
            section_data = self.settings[section]
            if isinstance(section_data, dict) and "data" in section_data:
                return section_data["data"], section_data["timestamp"]
        return {}, None

    def clear(self):
        """Clear all state data"""
        self.settings = {}
        self.save()
