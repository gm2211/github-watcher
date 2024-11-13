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
import traceback


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
        self.users_text.setText("\n".join(self.settings.users))
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
        self.refresh_value.setValue(self.settings.refresh.value)

        self.refresh_unit = QComboBox()
        self.refresh_unit.addItems(["seconds", "minutes", "hours"])
        index = self.refresh_unit.findText(self.settings.refresh.unit)
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

        self.files_warning = QSpinBox()
        self.files_warning.setRange(1, 100)
        self.files_warning.setValue(self.settings.thresholds.files.warning)
        files_layout.addRow("Warning Level:", self.files_warning)

        self.files_danger = QSpinBox()
        self.files_danger.setRange(1, 1000)
        self.files_danger.setValue(self.settings.thresholds.files.danger)
        files_layout.addRow("Danger Level:", self.files_danger)

        thresholds_layout.addWidget(files_group)

        # Additions thresholds
        additions_group = QGroupBox("Line Additions Thresholds")
        additions_layout = QFormLayout(additions_group)

        self.additions_warning = QSpinBox()
        self.additions_warning.setRange(1, 2000)
        self.additions_warning.setValue(self.settings.thresholds.additions.warning)
        additions_layout.addRow("Warning Level:", self.additions_warning)

        self.additions_danger = QSpinBox()
        self.additions_danger.setRange(1, 10000)
        self.additions_danger.setValue(self.settings.thresholds.additions.danger)
        additions_layout.addRow("Danger Level:", self.additions_danger)

        thresholds_layout.addWidget(additions_group)

        # Deletions thresholds
        deletions_group = QGroupBox("Line Deletions Thresholds")
        deletions_layout = QFormLayout(deletions_group)

        self.deletions_warning = QSpinBox()
        self.deletions_warning.setRange(1, 2000)
        self.deletions_warning.setValue(self.settings.thresholds.deletions.warning)
        deletions_layout.addRow("Warning Level:", self.deletions_warning)

        self.deletions_danger = QSpinBox()
        self.deletions_danger.setRange(1, 10000)
        self.deletions_danger.setValue(self.settings.thresholds.deletions.danger)
        deletions_layout.addRow("Danger Level:", self.deletions_danger)

        thresholds_layout.addWidget(deletions_group)

        # Age thresholds
        age_group = QGroupBox("PR Age Thresholds (days)")
        age_layout = QFormLayout(age_group)

        self.age_warning = QSpinBox()
        self.age_warning.setRange(1, 30)
        self.age_warning.setValue(self.settings.thresholds.age.warning)
        age_layout.addRow("Warning Level:", self.age_warning)

        self.age_danger = QSpinBox()
        self.age_danger.setRange(1, 90)
        self.age_danger.setValue(self.settings.thresholds.age.danger)
        age_layout.addRow("Danger Level:", self.age_danger)

        thresholds_layout.addWidget(age_group)

        # Recently Closed threshold
        recent_group = QGroupBox("Recently Closed Settings")
        recent_layout = QFormLayout(recent_group)

        self.recent_threshold = QSpinBox()
        self.recent_threshold.setRange(1, 30)
        self.recent_threshold.setValue(self.settings.thresholds.recently_closed_days)
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
        try:
            # Update users
            users_text = self.users_text.toPlainText()
            users = [u.strip() for u in users_text.split("\n") if u.strip()]
            self.settings.users = users

            # Update refresh settings
            self.settings.refresh.value = self.refresh_value.value()
            self.settings.refresh.unit = self.refresh_unit.currentText()

            # Update thresholds
            self.settings.thresholds.files.warning = self.files_warning.value()
            self.settings.thresholds.files.danger = self.files_danger.value()
            self.settings.thresholds.additions.warning = self.additions_warning.value()
            self.settings.thresholds.additions.danger = self.additions_danger.value()
            self.settings.thresholds.deletions.warning = self.deletions_warning.value()
            self.settings.thresholds.deletions.danger = self.deletions_danger.value()
            self.settings.thresholds.age.warning = self.age_warning.value()
            self.settings.thresholds.age.danger = self.age_danger.value()
            self.settings.thresholds.recently_closed_days = (
                self.recent_threshold.value()
            )

            # Save settings
            self.settings.save()
            return self.settings

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to get settings: {str(e)}")
            return None
