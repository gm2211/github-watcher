from dataclasses import dataclass, field
from typing import Dict, Set

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget

from .combo_box import MultiSelectComboBox
from .theme import Colors, Styles
from ..objects import PullRequest

ALL_AUTHORS = "All Authors"


@dataclass
class FilterState:
    """Strongly typed filter state"""

    show_drafts: bool = True
    group_by_user: bool = False
    selected_users: Set[str] = field(default_factory=lambda: {ALL_AUTHORS})

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility"""
        return {
            "show_drafts": self.show_drafts,
            "group_by_user": self.group_by_user,
            "selected_users": self.selected_users,
        }


class FiltersBar(QWidget):
    # has to be put here and not in init, unclear why (even putting it before parent __init__ call doesn't work)
    filters_changed_signal = pyqtSignal()

    def __init__(self):
        super().__init__(None)
        self.user_filter = MultiSelectComboBox(default_selection=ALL_AUTHORS)
        self.show_drafts_toggle = QCheckBox("Show Drafts")
        self.group_by_user_toggle = QCheckBox("Group by User")

        self.setObjectName("filtersBar")
        self.setStyleSheet(Styles.FILTERS)

        # Initialize state
        self.filter_state = FilterState()

        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 8, 16, 8)
        self.layout.setSpacing(16)

        # Create widgets
        self._setup_toggles()
        self._setup_user_filter()

        # Add stretch at the end
        self.layout.addStretch()

    def _setup_toggles(self):
        """Setup toggle checkboxes"""
        # Show drafts toggle
        self.show_drafts_toggle.setChecked(self.filter_state.show_drafts)
        self.show_drafts_toggle.stateChanged.connect(self._on_drafts_toggled)
        self.layout.addWidget(self.show_drafts_toggle)

        # Group by user toggle
        self.group_by_user_toggle.setChecked(self.filter_state.group_by_user)
        self.group_by_user_toggle.stateChanged.connect(self._on_grouping_toggled)
        self.layout.addWidget(self.group_by_user_toggle)

    def _setup_user_filter(self):
        """Setup user filter combo box"""
        # Container for filter and label
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)

        # Label
        label = QLabel("Filter by Author:")
        label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        filter_layout.addWidget(label)

        # Combo box
        self.user_filter.setStyleSheet(Styles.COMBO_BOX)
        self.user_filter.selectionChanged.connect(self._on_selected_users_changed)
        filter_layout.addWidget(self.user_filter)

        self.layout.addWidget(filter_container)

    def _on_drafts_toggled(self):
        self.filter_state.show_drafts = self.show_drafts_toggle.isChecked()
        self.filters_changed_signal.emit()

    def _on_grouping_toggled(self):
        self.filter_state.group_by_user = self.group_by_user_toggle.isChecked()
        self.filters_changed_signal.emit()

    def _on_selected_users_changed(self):
        self.filter_state.selected_users = self.user_filter.get_selected_items()
        self.filters_changed_signal.emit()

    def update_user_filter(self, users):
        """Update available users in the filter"""
        try:
            # Clear existing items
            self.user_filter.clear()

            # Add items
            all_users = [ALL_AUTHORS]
            if users:
                all_users.extend(sorted(users))
            self.user_filter.addItems(all_users)

        except Exception as e:
            print(f"Error updating user filter: {e}")

    def get_filter_state(self) -> FilterState:
        """Get current state of all filters"""
        return self.filter_state

    # weird impl - we're using dict structure to figure out if group_by_user is enabled
    def filter_prs_grouped_by_users(self, pr_data) -> Dict[str, list[PullRequest]]:
        """Filter PRs based on current filter state"""
        filtered_prs = {}

        # First apply user filter
        for user, prs in pr_data.items():
            if (
                ALL_AUTHORS not in self.filter_state.selected_users
                and user not in self.filter_state.selected_users
            ):
                continue

            # Apply draft filter
            filtered_user_prs = []
            for pr in prs:
                if not self.filter_state.show_drafts and pr.draft:
                    continue
                filtered_user_prs.append(pr)

            if filtered_user_prs:
                if self.filter_state.group_by_user:
                    # When grouping by user, keep the user structure
                    filtered_prs[user] = filtered_user_prs
                else:
                    # When not grouping by user, combine all PRs into a single list
                    filtered_prs.setdefault("all", []).extend(filtered_user_prs)

        return filtered_prs
