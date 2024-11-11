from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QScrollArea, QSizePolicy,
    QMessageBox, QApplication, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from datetime import timedelta

from src.github_auth import get_github_api_key
from src.github_prs import GitHubPRs
from src.settings import get_settings
from src.notifications import notify
from src.state import UIState

from .section_frame import SectionFrame
from .settings_dialog import SettingsDialog
from .refresh_worker import RefreshWorker
from .filters import FiltersBar
from .pr_card import create_pr_card
from .theme import Colors, Styles

class PRWatcherUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub PR Watcher")
        self.setStyleSheet(Styles.MAIN_WINDOW)
        self.workers = []
        self.refresh_worker = None

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create section frames first
        self.needs_review_frame = SectionFrame("Needs Review")
        self.changes_requested_frame = SectionFrame("Changes Requested")
        self.open_prs_frame = SectionFrame("Open PRs")
        self.recently_closed_frame = SectionFrame("Recently Closed")

        # Create header with buttons
        header_layout = QHBoxLayout()
        self._setup_header(header_layout)
        main_layout.addLayout(header_layout)

        # Create filters
        self.filters = FiltersBar()
        self.filters.filtersChanged.connect(self.apply_filters)
        main_layout.addWidget(self.filters)

        # Create scroll area for sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """
        )

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add sections to scroll area
        scroll_layout.addWidget(self.needs_review_frame)
        scroll_layout.addWidget(self.changes_requested_frame)
        scroll_layout.addWidget(self.open_prs_frame)
        scroll_layout.addWidget(self.recently_closed_frame)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Initialize state
        self.settings = get_settings()

    def _setup_header(self, header_layout):
        """Setup the header section with title and buttons"""
        # Left side: loading indicator and title
        left_layout = QHBoxLayout()

        # Loading indicator
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet(
            """
            QLabel {
                color: #0d6efd;
                font-size: 12px;
                padding: 0 5px;
            }
        """
        )
        self.loading_label.hide()
        left_layout.addWidget(self.loading_label)

        # Title
        title = QLabel("GitHub PR Watcher")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        left_layout.addWidget(title)

        header_layout.addLayout(left_layout)
        header_layout.addStretch()

        # Buttons container
        buttons_layout = QHBoxLayout()
        self._setup_buttons(buttons_layout)
        header_layout.addLayout(buttons_layout)

    def _setup_buttons(self, buttons_layout):
        """Setup the header buttons"""
        button_style = """
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
                font-size: 12px;
                height: 25px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """

        # Test notification button
        test_notif_btn = QPushButton("🔔 Test")
        test_notif_btn.clicked.connect(self.show_test_notification)
        test_notif_btn.setFixedWidth(80)
        test_notif_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(test_notif_btn)

        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setFixedWidth(80)
        refresh_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(refresh_btn)

        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setFixedWidth(80)
        settings_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(settings_btn)

    def show_test_notification(self):
        """Show a test notification"""
        notify("Test Notification", "This is a test notification from GitHub PR Watcher")

    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self)
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
            current_settings = get_settings()
            
            # Compare refresh settings
            old_refresh = current_settings.get("refresh", {})
            new_refresh = new_settings.get("refresh", {})
            if old_refresh != new_refresh:
                self._update_refresh_timer(new_refresh)

            # Store new settings
            self.settings = new_settings  # new_settings is a Settings instance

            # Update user filter and refresh data if users changed
            if new_settings.get("users") != current_settings.get("users"):
                self.update_user_filter()
                self.refresh_data()
            else:
                # Just update UI for threshold changes
                self._update_ui_with_current_data()

        except Exception as e:
            print(f"Error applying settings changes: {e}")
            import traceback
            traceback.print_exc()  # Print full stack trace for debugging
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def apply_filters(self):
        """Apply all current filters to the UI"""
        print("\nDebug - Applying filters")
        try:
            filter_state = self.filters.get_filter_state()
            print(f"Debug - Filter state: {filter_state}")

            # Update each section
            for frame in [
                self.open_prs_frame,
                self.needs_review_frame,
                self.changes_requested_frame,
                self.recently_closed_frame,
            ]:
                self._update_section(frame, frame.prs, filter_state)
        except Exception as e:
            print(f"Error applying filters: {e}")

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
            filtered_prs = []
            for user, prs in pr_data.items():
                if "All Authors" not in filter_state["selected_users"] and user not in filter_state["selected_users"]:
                    continue
                for pr in prs:
                    # Apply draft filter
                    if not filter_state["show_drafts"] and getattr(pr, "draft", False):
                        continue
                    filtered_prs.append(pr)

            # Update count
            frame.update_count(len(filtered_prs))

            # Create PR cards
            for pr in filtered_prs:
                card = create_pr_card(pr, self.settings)
                frame.content_layout.addWidget(card)

            frame.content_layout.addStretch()

        except Exception as e:
            print(f"Error updating section {frame.title}: {e}")

    def update_user_filter(self):
        """Update the user filter with current users"""
        try:
            users = self.settings.get("users", [])
            self.filters.update_user_filter(users)
        except Exception as e:
            print(f"Error updating user filter: {e}")

    def refresh_data(self):
        """Refresh PR data"""
        if hasattr(self, "refresh_worker") and self.refresh_worker and self.refresh_worker.isRunning():
            print("Debug - Refresh already in progress")
            return

        try:
            users = self.settings.get("users", [])
            if not users:
                print("Debug - No users configured")
                return

            self.refresh_worker = RefreshWorker(self.github_prs, users)
            self.refresh_worker.finished.connect(self._handle_refresh_complete)
            self.refresh_worker.error.connect(self._handle_refresh_error)
            self.workers.append(self.refresh_worker)
            self.refresh_worker.start()

            # Show loading state
            self._show_loading_state()

        except Exception as e:
            print(f"Error starting refresh: {e}")
            self._handle_refresh_error(str(e))

    def update_pr_lists(
        self,
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    ):
        """Update all PR lists in the UI"""
        print("\nDebug - Updating PR lists")
        try:
            # Store PR data in frames
            self.open_prs_frame.prs = open_prs_by_user
            self.needs_review_frame.prs = prs_awaiting_review_by_user
            self.changes_requested_frame.prs = prs_that_need_attention_by_user
            self.recently_closed_frame.prs = user_recently_closed_prs_by_user

            # Apply current filters
            self.apply_filters()

        except Exception as e:
            print(f"Error updating PR lists: {e}")

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
            self.update_pr_lists(*data)
            if self.refresh_worker in self.workers:
                self.workers.remove(self.refresh_worker)
            self.refresh_worker = None
        except Exception as e:
            print(f"Error handling refresh completion: {e}")

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
                refresh_settings = self.settings.get("refresh", {"value": 30, "unit": "seconds"})

            value = refresh_settings.get("value", 30)
            unit = refresh_settings.get("unit", "seconds")

            # Convert to milliseconds
            if unit == "seconds":
                interval = value * 1000
            elif unit == "minutes":
                interval = value * 60 * 1000
            else:  # hours
                interval = value * 60 * 60 * 1000

            print(f"Debug - Setting up refresh timer with interval: {interval}ms ({value} {unit})")

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
            value = refresh_settings.get("value", 30)
            unit = refresh_settings.get("unit", "seconds")
            
            if unit == "seconds":
                interval = value * 1000
            elif unit == "minutes":
                interval = value * 60 * 1000
            else:  # hours
                interval = value * 60 * 60 * 1000

            # Update timer
            self.auto_refresh_timer.setInterval(interval)
            if not self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.start()

            print(f"Debug - Timer updated: {value} {unit} ({interval}ms)")

        except Exception as e:
            print(f"Error updating refresh timer: {e}")

def open_ui(
    open_prs_by_user,
    prs_awaiting_review_by_user,
    prs_that_need_attention_by_user,
    user_recently_closed_prs_by_user,
    github_prs=None,
    settings=None,
):
    app = QApplication([])
    app.setStyle("Fusion")

    window = PRWatcherUI()

    # Use passed settings or load them
    if settings is None:
        settings = get_settings()
    window.settings = settings

    # Use passed GitHubPRs instance or create new one
    if github_prs is None:
        github_token = get_github_api_key()
        github_prs = GitHubPRs(
            github_token,
            recency_threshold=timedelta(days=1),
        )
    window.github_prs = github_prs

    # Initialize user filter before updating PR lists
    window.update_user_filter()

    # Update initial data
    window.update_pr_lists(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    )

    # Initialize refresh timer with current settings
    window.setup_refresh_timer(settings.get("refresh"))

    window.show()

    return app.exec() 