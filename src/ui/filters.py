from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget

from .combo_box import MultiSelectComboBox
from .theme import Colors, Styles


class FiltersBar(QWidget):
    filtersChanged = pyqtSignal()  # Signal when any filter changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filtersBar")
        self.setStyleSheet(Styles.FILTERS)
        
        # Initialize state
        self.filtersState = {
            "show_drafts": True,
            "group_by_user": False,
            "selected_users": {"All Authors"},
        }
        
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
        self.show_drafts_toggle = QCheckBox("Show Drafts")
        self.show_drafts_toggle.setChecked(True)
        self.show_drafts_toggle.setStyleSheet(Styles.CHECKBOX)
        self.show_drafts_toggle.stateChanged.connect(self._on_drafts_toggled)
        self.layout.addWidget(self.show_drafts_toggle)

        # Group by user toggle
        self.group_by_user_toggle = QCheckBox("Group by User")
        self.group_by_user_toggle.setStyleSheet(Styles.CHECKBOX)
        self.group_by_user_toggle.stateChanged.connect(self._on_grouping_toggled)
        self.layout.addWidget(self.group_by_user_toggle)

    def _setup_user_filter(self):
        """Setup user filter combo box"""
        # Container for filter and label
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        # Label
        label = QLabel("Filter by Author:")
        label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        filter_layout.addWidget(label)

        # Combo box
        self.user_filter = MultiSelectComboBox()
        self.user_filter.setStyleSheet(Styles.COMBO_BOX)
        self.user_filter.selectionChanged.connect(self.filtersChanged.emit)
        filter_layout.addWidget(self.user_filter)

        self.layout.addWidget(filter_container)

    def _on_drafts_toggled(self):
        self.filtersState["show_drafts"] = self.show_drafts_toggle.isChecked()
        self._update_filter_state()

    def _on_grouping_toggled(self):
        self.filtersState["group_by_user"] = self.group_by_user_toggle.isChecked()
        self._update_filter_state()

    def _update_filter_state(self):
        self.filtersState["selected_users"] = self.user_filter.getSelectedItems()
        self.filtersChanged.emit()

    def update_user_filter(self, users):
        """Update available users in the filter"""
        try:
            # Clear existing items
            self.user_filter.clear()

            # Add items
            items = ["All Authors"]
            if users:
                items.extend(sorted(users))
            self.user_filter.addItems(items)

        except Exception as e:
            print(f"Error updating user filter: {e}")

    def get_filter_state(self):
        """Get current state of all filters"""
        return {
            "show_drafts": self.show_drafts_toggle.isChecked(),
            "group_by_user": self.group_by_user_toggle.isChecked(),
            "selected_users": self.user_filter.getSelectedItems(),
        }
