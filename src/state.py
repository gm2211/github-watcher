import os
import json
from datetime import datetime
from typing import Dict, Any
from src.objects import PullRequest, User

class UIState:
    def __init__(self, state_file: str = "~/.github-pr-watcher-state.json"):
        self.state_file = os.path.expanduser(state_file)
        self.state: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        """Load state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Convert stored PR data back to PullRequest objects
                    for section in ['open', 'review', 'attention', 'closed']:
                        if section in data:
                            section_data = data[section]['data']
                            data[section]['data'] = {
                                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                                for user, prs in section_data.items()
                            }
                    return data
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
        return {}

    def save(self):
        """Save current state to file"""
        try:
            # Create a copy of state for serialization
            serializable_state = {}
            for section, section_data in self.state.items():
                if 'data' in section_data:
                    # Convert PullRequest objects to dictionaries
                    serializable_state[section] = {
                        'timestamp': section_data['timestamp'],
                        'data': {
                            user: [pr.to_dict() for pr in prs]
                            for user, prs in section_data['data'].items()
                        }
                    }
                else:
                    serializable_state[section] = section_data

            with open(self.state_file, 'w') as f:
                json.dump(serializable_state, f)
        except Exception as e:
            print(f"Warning: Failed to save state: {e}")

    def update_pr_data(self, section: str, data: dict):
        """Update PR data for a section"""
        self.state[section] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.save()

    def get_pr_data(self, section: str) -> tuple[dict, str]:
        """Get PR data and timestamp for a section"""
        if section in self.state:
            return (
                self.state[section]['data'],
                self.state[section]['timestamp']
            )
        return {}, None

    def clear(self):
        """Clear all state data"""
        self.state = {}
        self.save() 