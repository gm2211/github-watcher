import os
import sys
from datetime import timedelta

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from src.github_auth import get_github_api_key
from src.github_prs_client import GitHubPRsClient
from src.settings import Settings
from src.ui.main_window import MainWindow
from src.ui.state import UIState

VERSION = "1.0.0"


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    elif "Contents/Resources" in os.path.abspath(__file__):
        # Running from app bundle
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)


def main():
    # Add version flag support
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"GitHub PR Watcher v{VERSION}")
        return 0

    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName("GitHub PR Watcher")
    app.setApplicationVersion(VERSION)

    # Set app icon
    if os.path.exists(get_resource_path("resources/AppIcon.icns")):
        from PyQt6.QtGui import QIcon

        app.setWindowIcon(QIcon(get_resource_path("resources/AppIcon.icns")))

    try:
        # Load UI state and settings
        ui_state = UIState.load()
        settings = Settings.load()
        window = MainWindow(ui_state, settings)

        github_token = get_github_api_key()
        github_prs_client = GitHubPRsClient(
            github_token,
            recency_threshold=timedelta(days=1),
        )
        window.github_prs_client = github_prs_client
        window.populate_users_filter()

        # Load saved state and update UI before showing window
        open_prs, _ = window.state.get_pr_data("open")
        needs_review, _ = window.state.get_pr_data("review")
        changes_requested, _ = window.state.get_pr_data("attention")
        recently_closed, _ = window.state.get_pr_data("closed")

        # Update UI with saved data
        if any([open_prs, needs_review, changes_requested, recently_closed]):
            print("\nDebug - Loading saved PR data")
            window.update_pr_lists(
                open_prs, needs_review, changes_requested, recently_closed
            )

        # Initialize refresh timer with current settings
        window.setup_refresh_timer(settings.get("refresh"))

        window.show()

        # Schedule refresh after window is shown
        QTimer.singleShot(0, window.refresh_data)
        return app.exec()
    except Exception as e:
        print(f"Error fetching PR data: {e}")
        print("Please check your GitHub token and internet connection.")


if __name__ == "__main__":
    sys.exit(main())
