import os
import sys
import traceback
from datetime import timedelta

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.github_auth import get_github_api_key
from src.github_prs_client import GitHubPRsClient
from src.settings import Settings
from src.ui.main_window import MainWindow
from src.ui.ui_state import UIState

VERSION = "1.0.0"


def get_resource_path(relative_path):
    if "Contents/Resources" in os.path.abspath(__file__):
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
        window = MainWindow(github_prs_client, ui_state, settings)
        window.show()

        # Schedule refresh after window is shown
        QTimer.singleShot(0, window.refresh_data)
        return app.exec()
    except Exception as e:
        traceback.print_exc()
        print(f"Error fetching PR data: {e}")


if __name__ == "__main__":
    sys.exit(main())
