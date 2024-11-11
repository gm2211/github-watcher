import os
import json
from datetime import datetime
from typing import Dict, Any
from src.objects import PullRequest

class UIState:
    def __init__(self, state_file: str = "state.json"):
        # Store state.json next to main.py in src/
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Gets src/ directory
        self.state_file = os.path.join(script_dir, state_file)
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
                            section_data = data[section]
                            if isinstance(section_data, dict) and 'data' in section_data:
                                section_data['data'] = {
                                    user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                                    for user, prs in section_data['data'].items()
                                }
                    return data
        except Exception as e:
            print(f"Warning: Failed to load state: {e}")
            import traceback
            traceback.print_exc()
        return {}

    def save(self):
        """Save current state to file"""
        try:
            print(f"\nDebug - Saving state to {self.state_file}")
            print(f"Debug - Current state: {self.state}")
            
            # Create a copy of state for serialization
            serializable_state = {}
            for key, value in self.state.items():
                if key.endswith('_expanded'):  # UI state
                    serializable_state[key] = value
                elif isinstance(value, dict) and 'data' in value:  # PR data
                    serializable_state[key] = {
                        'timestamp': value['timestamp'],
                        'data': {
                            user: [pr.to_dict() for pr in prs]
                            for user, prs in value['data'].items()
                        }
                    }
                else:
                    serializable_state[key] = value

            print(f"Debug - Serializable state: {serializable_state}")
            
            with open(self.state_file, 'w') as f:
                json.dump(serializable_state, f, indent=2)
            print("Debug - State saved successfully")
            
        except Exception as e:
            print(f"Warning: Failed to save state: {e}")
            import traceback
            traceback.print_exc()

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
            section_data = self.state[section]
            if isinstance(section_data, dict) and 'data' in section_data:
                return (section_data['data'], section_data['timestamp'])
        return {}, None

    def clear(self):
        """Clear all state data"""
        self.state = {}
        self.save()