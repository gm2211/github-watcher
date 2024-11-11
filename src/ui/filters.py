from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal

from .combo_box import MultiSelectComboBox
from .theme import Colors, Styles

class FiltersBar(QWidget):
    filtersChanged = pyqtSignal()  # Signal when any filter changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_drafts = True
        self.group_by_user = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Show drafts toggle
        self.show_drafts_toggle = QCheckBox("Show Drafts")
        self.show_drafts_toggle.setChecked(True)
        self.show_drafts_toggle.setStyleSheet(Styles.CHECKBOX)
        self.show_drafts_toggle.stateChanged.connect(self._on_drafts_toggled)
        layout.addWidget(self.show_drafts_toggle)

        # Group by user toggle
        self.group_by_user_toggle = QCheckBox("Group by User")
        self.group_by_user_toggle.setStyleSheet(Styles.CHECKBOX)
        self.group_by_user_toggle.stateChanged.connect(self._on_grouping_toggled)
        layout.addWidget(self.group_by_user_toggle)

        # User filter
        user_filter_container = QWidget()
        user_filter_layout = QHBoxLayout(user_filter_container)
        user_filter_layout.setContentsMargins(0, 0, 0, 0)
        user_filter_layout.setSpacing(5)

        user_filter_label = QLabel("Filter by Author:")
        user_filter_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        user_filter_layout.addWidget(user_filter_label)

        # Initialize MultiSelectComboBox with multi-select enabled
        self.user_filter = MultiSelectComboBox()
        self.user_filter.setStyleSheet(Styles.COMBO_BOX)
        # Connect to filtersChanged signal
        self.user_filter.selectionChanged.connect(self.filtersChanged.emit)
        user_filter_layout.addWidget(self.user_filter)

        layout.addWidget(user_filter_container)
        layout.addStretch()

    def _on_drafts_toggled(self):
        self.show_drafts = self.show_drafts_toggle.isChecked()
        self.filtersChanged.emit()

    def _on_grouping_toggled(self):
        self.group_by_user = self.group_by_user_toggle.isChecked()
        self.filtersChanged.emit()

    def get_filter_state(self):
        """Get current state of all filters"""
        selected_users = self.user_filter.getSelectedItems()
        print(f"Debug - Selected users: {selected_users}")
        return {
            'show_drafts': self.show_drafts,
            'group_by_user': self.group_by_user,
            'selected_users': selected_users
        }

    def update_user_filter(self, users):
        """Update available users in the filter"""
        print("\nDebug - Updating user filter")
        try:
            # Clear existing items
            self.user_filter.clear()
            
            # Start with "All Authors"
            items = ["All Authors"]
            # Add users if provided
            if users:
                items.extend(sorted(users))
            print(f"Debug - Filter items: {items}")
            self.user_filter.addItems(items)
            
            # Select "All Authors" by default
            self.user_filter.setCurrentText("All Authors")
            
        except Exception as e:
            print(f"Error updating user filter: {e}")