import os
import sys
import traceback
from datetime import timedelta

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from github_pr_watcher.github_auth import get_github_api_key
from github_pr_watcher.github_prs_client import GitHubPRsClient
from github_pr_watcher.settings import Settings
from github_pr_watcher.ui.main_window import MainWindow
from github_pr_watcher.ui.ui_state import UIState

APP_VERSION = "1.24.0"


def get_resource_path(relative_path):
    if "Contents/Resources" in os.path.abspath(__file__):
        # Running from app bundle
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)


def main():
    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName(f"GitHub PR Watcher")
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(get_resource_path("resources/icon.png")))

    try:
        # Load UI state and settings
        ui_state = UIState.load()
        settings = Settings.load()
        github_token = get_github_api_key()
        github_prs_client = GitHubPRsClient(
            github_token,
            recency_threshold=timedelta(days=1),
        )
        window = MainWindow(github_prs_client, ui_state, settings, APP_VERSION)
        window.show()

        # Schedule refresh after window is shown
        QTimer.singleShot(0, window.refresh_data)
        return app.exec()
    except Exception as e:
        print(f"Error fetching PR data: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    sys.exit(main())
