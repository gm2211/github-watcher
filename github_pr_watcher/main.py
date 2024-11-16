import os
import sys

import tomllib as tomli
import traceback
from datetime import timedelta
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from github_pr_watcher.github_auth import get_github_api_key
from github_pr_watcher.github_prs_client import GitHubPRsClient
from github_pr_watcher.settings import Settings
from github_pr_watcher.ui.main_window import MainWindow
from github_pr_watcher.ui.ui_state import UIState


def get_version() -> str:
    """Read version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)
            return pyproject["tool"]["poetry"]["version"]
    except Exception as e:
        print(f"Error reading version from pyproject.toml: {e}")
        return "unknown"


def get_resource_path(relative_path):
    if "Contents/Resources" in os.path.abspath(__file__):
        # Running from app bundle
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)


def main():
    app_version = get_version()

    # Add version flag support
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"GitHub PR Watcher v{app_version}")
        return 0

    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName(f"GitHub PR Watcher")
    app.setApplicationVersion(app_version)
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
        window = MainWindow(github_prs_client, ui_state, settings, app_version)
        window.show()

        # Schedule refresh after window is shown
        QTimer.singleShot(0, window.refresh_data)
        return app.exec()
    except Exception as e:
        traceback.print_exc()
        print(f"Error fetching PR data: {e}")


if __name__ == "__main__":
    sys.exit(main())
