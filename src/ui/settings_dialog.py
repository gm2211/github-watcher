from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.settings = settings

        layout = QVBoxLayout(self)

        # Create tabs
        tabs = QTabWidget()

        # Users tab
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)

        # Users list
        users_group = QGroupBox("GitHub Users to Watch")
        users_group_layout = QVBoxLayout(users_group)

        self.users_text = QTextEdit()
        self.users_text.setPlaceholderText("Enter GitHub usernames, one per line")
        current_users = self.settings.get("users", [])
        self.users_text.setText("\n".join(current_users))
        users_group_layout.addWidget(self.users_text)

        users_layout.addWidget(users_group)
        tabs.addTab(users_tab, "Users")

        # Timing tab
        timing_tab = QWidget()
        timing_layout = QFormLayout(timing_tab)

        # Refresh settings
        refresh_group = QGroupBox("Refresh Settings")
        refresh_layout = QFormLayout(refresh_group)

        self.refresh_value = QSpinBox()
        self.refresh_value.setRange(1, 60)
        current_refresh = self.settings.get("refresh", {})
        self.refresh_value.setValue(current_refresh.get("value", 30))

        self.refresh_unit = QComboBox()
        self.refresh_unit.addItems(["seconds", "minutes", "hours"])
        current_unit = current_refresh.get("unit", "seconds")
        index = self.refresh_unit.findText(current_unit)
        if index >= 0:
            self.refresh_unit.setCurrentIndex(index)

        refresh_row = QHBoxLayout()
        refresh_row.addWidget(self.refresh_value)
        refresh_row.addWidget(self.refresh_unit)

        refresh_layout.addRow("Refresh Interval:", refresh_row)

        timing_layout.addWidget(refresh_group)
        tabs.addTab(timing_tab, "Timing")

        # Thresholds tab
        thresholds_tab = QWidget()
        thresholds_layout = QVBoxLayout(thresholds_tab)

        # Files thresholds
        files_group = QGroupBox("Files Changed Thresholds")
        files_layout = QFormLayout(files_group)

        current_thresholds = self.settings.get("thresholds", {})
        files_thresholds = current_thresholds.get("files", {})

        self.files_warning = QSpinBox()
        self.files_warning.setRange(1, 100)
        self.files_warning.setValue(files_thresholds.get("warning", 10))
        files_layout.addRow("Warning Level:", self.files_warning)

        self.files_danger = QSpinBox()
        self.files_danger.setRange(1, 1000)
        self.files_danger.setValue(files_thresholds.get("danger", 50))
        files_layout.addRow("Danger Level:", self.files_danger)

        thresholds_layout.addWidget(files_group)

        # Lines changed thresholds
        lines_group = QGroupBox("Lines Changed Thresholds")
        lines_layout = QFormLayout(lines_group)

        lines_thresholds = current_thresholds.get("lines", {})

        self.lines_warning = QSpinBox()
        self.lines_warning.setRange(1, 1000)
        self.lines_warning.setValue(lines_thresholds.get("warning", 500))
        lines_layout.addRow("Warning Level:", self.lines_warning)

        self.lines_danger = QSpinBox()
        self.lines_danger.setRange(1, 10000)
        self.lines_danger.setValue(lines_thresholds.get("danger", 1000))
        lines_layout.addRow("Danger Level:", self.lines_danger)

        thresholds_layout.addWidget(lines_group)

        # Recently Closed threshold
        recent_group = QGroupBox("Recently Closed Settings")
        recent_layout = QFormLayout(recent_group)

        self.recent_threshold = QSpinBox()
        self.recent_threshold.setRange(1, 30)
        self.recent_threshold.setValue(
            current_thresholds.get("recently_closed_days", 7)
        )
        recent_layout.addRow("Show PRs closed within (days):", self.recent_threshold)

        thresholds_layout.addWidget(recent_group)
        thresholds_layout.addStretch()

        tabs.addTab(thresholds_tab, "Thresholds")
        layout.addWidget(tabs)

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        """Get current settings from dialog"""
        print("\nDebug - Getting settings from dialog")
        try:

            # Update users
            users_text = self.users_text.toPlainText()
            users = [u.strip() for u in users_text.split("\n") if u.strip()]
            print(f"Debug - Users: {users}")
            self.settings.set("users", users)

            # Update refresh settings
            refresh = {
                "value": self.refresh_value.value(),
                "unit": self.refresh_unit.currentText(),
            }
            print(f"Debug - Refresh settings: {refresh}")
            self.settings.set("refresh", refresh)

            # Update thresholds
            thresholds = {
                "files": {
                    "warning": self.files_warning.value(),
                    "danger": self.files_danger.value(),
                },
                "lines": {
                    "warning": self.lines_warning.value(),
                    "danger": self.lines_danger.value(),
                },
                "recently_closed_days": self.recent_threshold.value(),
            }
            print(f"Debug - Thresholds: {thresholds}")
            self.settings.set("thresholds", thresholds)

            return self.settings  # Return the Settings instance

        except Exception as e:
            print(f"Error getting settings from dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to get settings: {str(e)}")
            return None
