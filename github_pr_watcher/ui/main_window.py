import traceback
from typing import Dict

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
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

from github_pr_watcher.github_prs_client import GitHubPRsClient, PRSection
from github_pr_watcher.notifications import notify
from github_pr_watcher.objects import PullRequest
from github_pr_watcher.settings import RefreshInterval, Settings
from github_pr_watcher.ui.filters import FiltersBar, FilterState
from github_pr_watcher.ui.pr_card import create_pr_card
from github_pr_watcher.ui.refresh_worker import RefreshWorker
from github_pr_watcher.ui.section_frame import SectionFrame
from github_pr_watcher.ui.settings_dialog import SettingsDialog
from github_pr_watcher.ui.themes import Colors, Styles
from github_pr_watcher.ui.ui_state import SectionName, UIState


class MainWindow(QMainWindow):

    def __init__(
        self, github_prs_client: GitHubPRsClient, ui_state: UIState, settings: Settings, app_version: str
    ):
        super().__init__()
        self.github_prs_client = github_prs_client
        self.ui_state: UIState = ui_state
        self.settings: Settings = settings
        self.auto_refresh_timer: QTimer | None = None
        self.setWindowTitle(f"GitHub PR Watcher - v{app_version}")
        self.setStyleSheet(Styles.MAIN_WINDOW)
        self.workers = []
        self.refresh_worker = None
        self.is_refreshing = False

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Create section frames first
        self.needs_review_frame = SectionFrame(SectionName.NEEDS_REVIEW, self.ui_state)
        self.changes_requested_frame = SectionFrame(
            SectionName.CHANGES_REQUESTED, self.ui_state
        )
        self.open_prs_frame = SectionFrame(SectionName.OPEN_PRS, self.ui_state)
        self.recently_closed_frame = SectionFrame(
            SectionName.RECENTLY_CLOSED, self.ui_state
        )

        # Create header with buttons and filters
        header_container = QWidget()
        header_container.setObjectName(Styles.HEADER_CONTAINER_CSS_NAME)
        header_container.setStyleSheet(Styles.HEADER)

        # Create a vertical layout for header + filters
        header_vertical = QVBoxLayout(header_container)
        header_vertical.setContentsMargins(0, 0, 0, 0)
        header_vertical.setSpacing(0)

        # Header content (title and buttons)
        header_content = QWidget()
        header_layout = QHBoxLayout(header_content)
        header_layout.setContentsMargins(16, 16, 16, 8)

        # Left side: loading indicator and title
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)

        # Loading indicator
        self.loading_label = QLabel("Refreshing Data...")
        self.loading_label.setObjectName(Styles.LOADING_LABEL_CSS_NAME)
        self.loading_label.hide()
        left_layout.addWidget(self.loading_label)

        # Title
        title = QLabel("GitHub PR Watcher")
        title.setObjectName(Styles.HEADER_TITLE_CSS_NAME)
        left_layout.addWidget(title)

        header_layout.addLayout(left_layout)
        header_layout.addStretch()

        # Buttons container
        buttons_layout = QHBoxLayout()
        self._setup_buttons(buttons_layout)
        header_layout.addLayout(buttons_layout)

        # Add header content to vertical layout
        header_vertical.addWidget(header_content)

        # Create and add filters
        self.filter_bar = FiltersBar()
        self.filter_bar.filters_changed_signal.connect(self.apply_filters)
        header_vertical.addWidget(self.filter_bar)

        # Add header container to main layout
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

        # Populate data and setup background refresh
        self.populate_users_filter()
        self.apply_filters()
        self.setup_or_reset_refresh_timer(settings.refresh)

    def _setup_buttons(self, buttons_layout):
        """Setup the header buttons"""
        # Test notification button
        test_notif_btn = QPushButton("🔔 Test")
        test_notif_btn.clicked.connect(self.show_test_notification)
        test_notif_btn.setFixedWidth(80)
        test_notif_btn.setStyleSheet(Styles.BUTTON)
        buttons_layout.addWidget(test_notif_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setFixedWidth(80)
        refresh_btn.setStyleSheet(Styles.BUTTON)
        buttons_layout.addWidget(refresh_btn)

        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
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
            settings_dialog = SettingsDialog(self.settings)
            if settings_dialog.exec() == QDialog.DialogCode.Accepted:
                settings = settings_dialog.get_settings()
                if settings:
                    settings.save()
                    self._apply_settings_changes(settings)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show settings: {str(e)}")

    def _apply_settings_changes(self, new_settings):
        """Apply changes from settings dialog"""
        try:
            if not new_settings:  # If settings dialog returned None
                return

            # Get current settings from the Settings instance
            previous_settings = self.settings

            # Compare refresh settings
            if previous_settings.refresh != new_settings.refresh:
                self.setup_or_reset_refresh_timer(new_settings.refresh)

            # Store new settings
            self.settings = new_settings
            self.populate_users_filter()

            # Update user filter and refresh data if users changed
            if new_settings.users != previous_settings.users:
                self.refresh_data()  # This will also apply filters / update UI
            else:
                # Even if users haven't changed, we should reapply filters
                # because thresholds might have changed
                self.apply_filters()

        except Exception as e:
            print(f"Error applying settings: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def apply_filters(self):
        """Apply filters and update UI"""
        try:
            # Get current filter state
            filter_state: FilterState = self.filter_bar.get_filter_state()

            # First get needs review PRs to filter them out from open PRs
            needs_review_data, _ = self.ui_state.get_pr_data(SectionName.NEEDS_REVIEW)
            needs_review_numbers = set()
            if needs_review_data:
                for prs in needs_review_data.values():
                    needs_review_numbers.update(pr.number for pr in prs)

            # Update each section with filtered data
            for frame in [
                self.open_prs_frame,
                self.needs_review_frame,
                self.changes_requested_frame,
                self.recently_closed_frame,
            ]:
                # Get PR data - returns tuple of (data, timestamp)
                pr_data, _ = self.ui_state.get_pr_data(frame.name)
                if pr_data is None:
                    continue

                # Clear existing content
                if frame.content_layout:
                    while frame.content_layout.count():
                        item = frame.content_layout.takeAt(0)
                        if widget := item.widget():
                            widget.deleteLater()

                # Filter out needs review PRs from open PRs section
                if frame.name == SectionName.OPEN_PRS:
                    filtered_data = {}
                    for user, prs in pr_data.items():
                        filtered_prs = [pr for pr in prs if pr.number not in needs_review_numbers]
                        if filtered_prs:
                            filtered_data[user] = filtered_prs
                    pr_data = filtered_data

                # Filter PRs
                filtered_prs = self.filter_bar.filter_prs_grouped_by_users(pr_data)
                total_prs = 0

                if filter_state.group_by_user:
                    # Group by user visualization
                    for user, user_prs in filtered_prs.items():
                        if not user_prs:
                            continue

                        # Add user header
                        user_header = QLabel(f"Author: {user}")
                        user_header.setStyleSheet(
                            f"""
                            QLabel {{
                                color: {Colors.TEXT_SECONDARY};
                                font-size: 12px;
                                font-weight: bold;
                                padding: 5px 0;
                            }}
                            """
                        )
                        frame.content_layout.addWidget(user_header)

                        # Add PR cards for this user
                        for pr in user_prs:
                            card = create_pr_card(pr, self.settings)
                            frame.content_layout.addWidget(card)
                            total_prs += 1

                        # Add spacing between user sections
                        spacer = QWidget()
                        spacer.setFixedHeight(10)
                        frame.content_layout.addWidget(spacer)

                else:
                    # Flat visualization (no grouping)
                    all_prs = filtered_prs.get("all", [])
                    for pr in all_prs:
                        card = create_pr_card(pr, self.settings)
                        frame.content_layout.addWidget(card)
                        total_prs += 1

                # Add stretch at the end
                frame.content_layout.addStretch()

                # Update count
                frame.update_count(total_prs)

        except Exception as e:
            print(f"Error applying filters: {e}")
            traceback.print_exc()

    def populate_users_filter(self):
        """Update the user filter with current users"""
        try:
            self.filter_bar.update_user_filter(self.settings.users)
        except Exception as e:
            print(f"Error updating user filter: {e}")
            traceback.print_exc()

    def refresh_data(self):
        """Refresh PR data"""
        if self.is_refreshing:
            return

        try:
            users = self.settings.users
            if not users:
                return

            self.is_refreshing = True
            self._show_loading_state()

            self.refresh_worker = RefreshWorker(
                self.github_prs_client,
                users,
                settings=self.settings,  # Pass settings to worker
            )
            self.refresh_worker.finished.connect(self._handle_refresh_complete)
            self.refresh_worker.error.connect(self._handle_refresh_error)
            self.workers.append(self.refresh_worker)
            self.refresh_worker.start()

        except Exception as e:
            self._handle_refresh_error(str(e))
            self.is_refreshing = False

    def _show_loading_state(self):
        """Show loading state in UI"""

        self.loading_label.show()

    def _hide_loading_state(self):
        """Hide loading state in UI"""

        self.loading_label.hide()

    def _handle_refresh_complete(
        self,
        prs_by_author_by_section: Dict[PRSection, Dict[str, list[(PullRequest, bool)]]],
    ):
        """Handle completion of refresh operation"""
        try:
            # Save each section's data
            self.ui_state.update_pr_data(
                SectionName.OPEN_PRS, prs_by_author_by_section.get(PRSection.OPEN, {})
            )
            self.ui_state.update_pr_data(
                SectionName.NEEDS_REVIEW,
                prs_by_author_by_section.get(PRSection.NEEDS_REVIEW, {}),
            )
            self.ui_state.update_pr_data(
                SectionName.CHANGES_REQUESTED,
                prs_by_author_by_section.get(PRSection.CHANGED_REQUESTED, {}),
            )
            self.ui_state.update_pr_data(
                SectionName.RECENTLY_CLOSED,
                prs_by_author_by_section.get(PRSection.CLOSED, {}),
            )
            self.ui_state.save()
            self.apply_filters()

            if self.refresh_worker in self.workers:
                self.workers.remove(self.refresh_worker)
            self.refresh_worker = None

        except Exception as e:
            print(f"Error handling refresh completion: {e}")
            traceback.print_exc()
        finally:
            self._hide_loading_state()
            self.is_refreshing = False

    def _handle_refresh_error(self, error_msg):
        """Handle refresh operation error"""
        self._hide_loading_state()
        QMessageBox.critical(self, "Error", f"Failed to refresh data: {error_msg}")
        if self.refresh_worker in self.workers:
            self.workers.remove(self.refresh_worker)
        self.refresh_worker = None
        self.is_refreshing = False

    def setup_or_reset_refresh_timer(self, refresh_interval: RefreshInterval):
        """Setup the refresh timer"""
        try:
            if self.auto_refresh_timer is not None:
                self.auto_refresh_timer.stop()

            # Create and start new timer
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.refresh_data)
            self.auto_refresh_timer.start(refresh_interval.to_millis())
        except Exception as e:
            print(f"Error setting up refresh timer: {e}")

    def showEvent(self, event):
        """Handle window show event"""
        super().showEvent(event)
