import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.ui import open_ui
from src.github_auth import get_github_api_key
from src.github_prs import GitHubPRs
from datetime import timedelta
from PyQt6.QtCore import QTimer
from src.state import UIState
from src.settings import get_settings

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

    settings = get_settings()
    users = settings.get("users", [])
    if not users:
        window = open_ui({}, {}, {}, {})
        return app.exec()

    try:
        github_token = get_github_api_key()
        github_prs = GitHubPRs(
            github_token,
            recency_threshold=timedelta(days=1),
        )

        # Load UI state
        ui_state = UIState()
        initial_data = (
            ui_state.get_pr_data("open")[0],
            ui_state.get_pr_data("review")[0],
            ui_state.get_pr_data("attention")[0],
            ui_state.get_pr_data("closed")[0]
        )

        window = open_ui(*initial_data, github_prs=github_prs, settings=settings.all)
        
        # Schedule immediate refresh
        QTimer.singleShot(0, window.refresh_data)

        return app.exec()

    except Exception as e:
        print(f"Error fetching PR data: {e}")
        print("Please check your GitHub token and internet connection.")
        window = open_ui({}, {}, {}, {})
        return app.exec()


if __name__ == "__main__":
    sys.exit(main())
