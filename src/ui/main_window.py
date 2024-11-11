import traceback

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.github_prs_client import GitHubPRsClient
from src.notifications import notify
from src.settings import Settings
from src.ui.filters import FiltersBar
from src.ui.pr_card import create_pr_card
from src.ui.refresh_worker import RefreshWorker
from src.ui.section_frame import SectionFrame
from src.ui.settings_dialog import SettingsDialog
from src.ui.state import UIState
from src.ui.theme import Styles


class MainWindow(QMainWindow):
    def __init__(self, state, settings: Settings):
        super().__init__()
        self.auto_refresh_timer: QTimer | None = None
        self.state = state
        self.settings = settings
        self.setWindowTitle("GitHub PR Watcher")
        self.setStyleSheet(Styles.MAIN_WINDOW)
        self.workers = []
        self.refresh_worker = None

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Create section frames first
        self.needs_review_frame = SectionFrame("Needs Review", self.state)
        self.changes_requested_frame = SectionFrame("Changes Requested", self.state)
        self.open_prs_frame = SectionFrame("Open PRs", self.state)
        self.recently_closed_frame = SectionFrame("Recently Closed", self.state)

        # Create header with buttons and filters
        header_container = QWidget()
        header_container.setObjectName("headerContainer")
        header_container.setStyleSheet(Styles.HEADER)

        # Create a vertical layout for header + filters
        header_vertical = QVBoxLayout(header_container)
        header_vertical.setContentsMargins(0, 0, 0, 0)
        header_vertical.setSpacing(0)

        # Header content
        header_content = QWidget()
        header_layout = QHBoxLayout(header_content)
        header_layout.setContentsMargins(16, 16, 16, 16)

        # Left side: loading indicator and title
        left_layout = QHBoxLayout()

        # Loading indicator
        self.loading_label = QLabel("Loading...")
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.hide()
        left_layout.addWidget(self.loading_label)

        # Title
        title = QLabel("GitHub PR Watcher")
        title.setObjectName("headerTitle")
        left_layout.addWidget(title)

        header_layout.addLayout(left_layout)
        header_layout.addStretch()

        # Buttons container
        buttons_layout = QHBoxLayout()
        self._setup_buttons(buttons_layout)
        header_layout.addLayout(buttons_layout)

        # Add header content to vertical layout
        header_vertical.addWidget(header_content)

        # Create filters
        self.filters = FiltersBar()
        self.filters.filtersChanged.connect(self.apply_filters)
        header_vertical.addWidget(self.filters)

        self.main_layout.addWidget(header_container)

        # Create scroll area for sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(Styles.SCROLL_AREA)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # Add sections to scroll area
        scroll_layout.addWidget(self.needs_review_frame, 1)
        scroll_layout.addWidget(self.changes_requested_frame, 1)
        scroll_layout.addWidget(self.open_prs_frame, 1)
        scroll_layout.addWidget(self.recently_closed_frame, 1)

        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area, 1)

        # Load and display saved PR data
        open_prs, _ = self.state.get_pr_data("open")
        needs_review, _ = self.state.get_pr_data("review")
        changes_requested, _ = self.state.get_pr_data("attention")
        recently_closed, _ = self.state.get_pr_data("closed")

        # Update UI with saved data
        self.update_pr_lists(open_prs, needs_review, changes_requested, recently_closed)

    def _setup_buttons(self, buttons_layout):
        """Setup the header buttons"""
        # Test notification button
        test_notif_btn = QPushButton("🔔 Test")
        test_notif_btn.clicked.connect(self.show_test_notification)
        test_notif_btn.setFixedWidth(80)
        test_notif_btn.setStyleSheet(Styles.BUTTON)
        buttons_layout.addWidget(test_notif_btn)

        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setFixedWidth(80)
        refresh_btn.setStyleSheet(Styles.BUTTON)
        buttons_layout.addWidget(refresh_btn)

        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setFixedWidth(80)
        settings_btn.setStyleSheet(Styles.BUTTON)
        buttons_layout.addWidget(settings_btn)

    @staticmethod
    def show_test_notification():
        """Show a test notification"""
        notify(
            "Test Notification", "This is a test notification from GitHub PR Watcher"
        )

    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self, self.settings)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                settings = dialog.get_settings()
                if settings:
                    self._apply_settings_changes(settings)
        except Exception as e:
            print(f"Error showing settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show settings: {str(e)}")

    def _apply_settings_changes(self, new_settings):
        """Apply changes from settings dialog"""
        try:
            if not new_settings:  # If settings dialog returned None
                return

            # Get current settings from the Settings instance
            current_settings = self.settings

            # Compare refresh settings
            old_refresh = current_settings.get("refresh", {})
            new_refresh = new_settings.get("refresh", {})
            if old_refresh != new_refresh:
                self._update_refresh_timer(new_refresh)

            # Store new settings
            self.settings = new_settings  # new_settings is a Settings instance

            # Update user filter and refresh data if users changed
            if new_settings.get("users") != current_settings.get("users"):
                self.populate_users_filter()
                self.refresh_data()
            else:
                # Just update UI for threshold changes
                self._update_ui_with_current_data()

        except Exception as e:
            print(f"Error applying settings changes: {e}")
            traceback.print_exc()  # Print full stack trace for debugging
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def apply_filters(
        self,
        open_prs=None,
        needs_review=None,
        needs_attention=None,
        recently_closed=None,
    ):
        """Apply filters to PR lists"""
        print("\nDebug - Applying filters")
        try:
            filter_state = self.filters.filtersState  # Use the property directly
            print(f"Debug - Filter state: {filter_state}")

            # Update each section with filtered data
            sections = [
                ("Open PRs", self.open_prs_frame, open_prs),
                ("Needs Review", self.needs_review_frame, needs_review),
                ("Changes Requested", self.changes_requested_frame, needs_attention),
                ("Recently Closed", self.recently_closed_frame, recently_closed),
            ]

            for title, frame, data in sections:
                print(f"\nDebug - Updating section: {title}")
                if data is not None:
                    self._update_section(
                        frame, data, filter_state
                    )  # Pass filter_state here
        except Exception as e:
            print(f"Error applying filters: {e}")
            traceback.print_exc()

    def _update_section(self, frame, pr_data, filter_state):
        """Update a section with filtered PR data"""
        print(f"\nDebug - Updating section: {frame.title}")
        try:
            # Clear existing content
            if frame.content_layout:
                while frame.content_layout.count():
                    item = frame.content_layout.takeAt(0)
                    if widget := item.widget():
                        widget.deleteLater()

            # Filter and group PRs
            filtered_prs = _filter_prs(pr_data, filter_state)

            # Update count
            frame.update_count(len(filtered_prs))

            # Create PR cards
            for pr in filtered_prs:
                card = create_pr_card(pr, self.settings)
                frame.content_layout.addWidget(card)

            frame.content_layout.addStretch()

        except Exception as e:
            print(f"Error updating section {frame.title}: {e}")

    def populate_users_filter(self):
        """Update the user filter with current users"""
        try:
            users = self.settings.get("users", [])
            self.filters.update_user_filter(users)
        except Exception as e:
            print(f"Error updating user filter: {e}")

    def refresh_data(self):
        """Refresh PR data"""
        if (
            hasattr(self, "refresh_worker")
            and self.refresh_worker
            and self.refresh_worker.isRunning()
        ):
            print("Debug - Refresh already in progress")
            return

        try:
            users = self.settings.get("users", [])
            if not users:
                print("Debug - No users configured")
                return

            self.refresh_worker = RefreshWorker(self.github_prs_client, users)
            self.refresh_worker.finished.connect(self._handle_refresh_complete)
            self.refresh_worker.error.connect(self._handle_refresh_error)
            self.workers.append(self.refresh_worker)
            self.refresh_worker.start()

            self._show_loading_state()

        except Exception as e:
            print(f"Error starting refresh: {e}")
            self._handle_refresh_error(str(e))

    def update_pr_lists(
        self,
        open_prs_by_user=None,
        prs_awaiting_review_by_user=None,
        prs_that_need_attention_by_user=None,
        user_recently_closed_prs_by_user=None,
    ):
        """Update all PR lists"""
        print("\nDebug - Updating PR lists")

        # Apply filters
        self.apply_filters(
            open_prs_by_user,
            prs_awaiting_review_by_user,
            prs_that_need_attention_by_user,
            user_recently_closed_prs_by_user,
        )

        # Save UI state after updating lists
        try:
            print("\nDebug - Saving UI state after updating lists")

            for section in [
                ("Needs Review", self.needs_review_frame),
                ("Changes Requested", self.changes_requested_frame),
                ("Open PRs", self.open_prs_frame),
                ("Recently Closed", self.recently_closed_frame),
            ]:
                title, frame = section
                key = f"section_{title}_expanded"
                self.state.settings[key] = frame.is_expanded
                print(f"Debug - Saving {key}={frame.is_expanded}")

            self.state.save()
            print("Debug - UI state saved successfully")

        except Exception as e:
            print(f"Error saving UI state: {e}")
            traceback.print_exc()

    def _show_loading_state(self):
        """Show loading state in UI"""
        print("\nDebug - Showing loading state")
        self.loading_label.show()
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame,
        ]:
            frame.start_loading()

    def _hide_loading_state(self):
        """Hide loading state in UI"""
        print("\nDebug - Hiding loading state")
        self.loading_label.hide()
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame,
        ]:
            frame.stop_loading()

    def _handle_refresh_complete(self, data):
        """Handle completion of refresh operation"""
        print("\nDebug - Refresh complete")
        try:
            self._hide_loading_state()

            # Unpack data tuple
            open_prs, needs_review, changes_requested, recently_closed = data

            # Save each section's data
            self.state.update_pr_data("open", open_prs)
            self.state.update_pr_data("review", needs_review)
            self.state.update_pr_data("attention", changes_requested)
            self.state.update_pr_data("closed", recently_closed)

            # Update UI
            self.update_pr_lists(*data)

            if self.refresh_worker in self.workers:
                self.workers.remove(self.refresh_worker)
            self.refresh_worker = None

        except Exception as e:
            print(f"Error handling refresh completion: {e}")
            traceback.print_exc()

    def _handle_refresh_error(self, error_msg):
        """Handle refresh operation error"""
        print(f"\nDebug - Refresh error: {error_msg}")
        self._hide_loading_state()
        QMessageBox.critical(self, "Error", f"Failed to refresh data: {error_msg}")
        if self.refresh_worker in self.workers:
            self.workers.remove(self.refresh_worker)
        self.refresh_worker = None

    def setup_refresh_timer(self, refresh_settings=None):
        """Setup the refresh timer"""
        try:
            if not refresh_settings:
                refresh_settings = self.settings.get(
                    "refresh", {"value": 30, "unit": "seconds"}
                )

            interval, unit, value = self.calc_interval(refresh_settings)

            print(
                f"Debug - Setting up refresh timer with interval: {interval}ms ({value} {unit})"
            )

            # Stop existing timer if it exists
            if hasattr(self, "auto_refresh_timer"):
                self.auto_refresh_timer.stop()
                print("Debug - Stopped existing timer")

            # Create and start new timer
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.refresh_data)
            self.auto_refresh_timer.start(interval)
            print("Debug - Started new timer")

        except Exception as e:
            print(f"Error setting up refresh timer: {e}")

    def _update_ui_with_current_data(self):
        """Update UI with current data (after settings change)"""
        self.apply_filters()

    def _update_refresh_timer(self, refresh_settings):
        """Update the refresh timer with new settings"""
        print("\nDebug - Updating refresh timer")
        try:
            # Create timer if it doesn't exist
            if not hasattr(self, "auto_refresh_timer"):
                self.auto_refresh_timer = QTimer(self)
                self.auto_refresh_timer.timeout.connect(self.refresh_data)

            # Calculate interval
            interval, unit, value = self.calc_interval(refresh_settings)

            # Update timer
            self.auto_refresh_timer.setInterval(interval)
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start()

            print(f"Debug - Timer updated: {value} {unit} ({interval}ms)")

        except Exception as e:
            print(f"Error updating refresh timer: {e}")

    def calc_interval(self, refresh_settings):
        value = refresh_settings.get("value", 30)
        unit = refresh_settings.get("unit", "seconds")
        if unit == "seconds":
            interval = value * 1000
        elif unit == "minutes":
            interval = value * 60 * 1000
        else:  # hours
            interval = value * 60 * 60 * 1000
        return interval, unit, value

    def refresh_complete(self):
        """Handle refresh completion"""
        print("\nDebug - Refresh complete")
        self.hide_loading()
        self.update_pr_lists()

        # Save UI state after refresh
        try:
            for section in [
                ("Needs Review", self.needs_review_frame),
                ("Changes Requested", self.changes_requested_frame),
                ("Open PRs", self.open_prs_frame),
                ("Recently Closed", self.recently_closed_frame),
            ]:
                title, frame = section
                key = f"section_{title}_expanded"
                self.state.settings[key] = frame.is_expanded

            print("\nDebug - Saving UI state after refresh")
            print(f"Debug - State before save: {self.state.settings}")
            self.state.save()
            print("Debug - UI state saved successfully")

        except Exception as e:
            print(f"Error saving UI state: {e}")
            traceback.print_exc()

    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
        # Schedule refresh after window is shown
        QTimer.singleShot(0, self.refresh_data)


def open_ui(
    app: QApplication,
    github_prs_client: GitHubPRsClient,
    ui_state: UIState,
    settings: Settings,
):
    pass


def _filter_prs(pr_data, filter_state):
    """Filter PRs based on the filter state"""
    filtered_prs = []
    for user, prs in pr_data.items():
        if (
            "All Authors" not in filter_state["selected_users"]
            and user not in filter_state["selected_users"]
        ):
            continue
        for pr in prs:
            # Apply draft filter
            if not filter_state["show_drafts"] and getattr(pr, "draft", False):
                continue
            filtered_prs.append(pr)
    return filtered_prs
