from typing import Dict, List, Tuple

from PyQt6.QtCore import pyqtSignal, QThread

from github_pr_watcher.github_prs_client import PRSection
from github_pr_watcher.objects import PullRequest


class RefreshWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, github_prs_client, users, settings=None, section=None):
        super().__init__()
        self.github_prs_client = github_prs_client
        self.users = users
        self.settings = settings
        self.section = section
        self._shutdown = False

    def run(self):
        try:
            # Check if already cancelled before starting
            if self._shutdown:
                return

            # Get PR data
            prs_by_author_by_section: Dict[
                PRSection, Dict[str, List[Tuple[PullRequest, bool]]]
            ] = self.github_prs_client.get_pr_data(
                self.users, self.section, settings=self.settings
            )

            # Check if cancelled during execution
            if self._shutdown:
                return

            if prs_by_author_by_section is not None:
                self.progress.emit("Completed refresh")
                self.finished.emit(prs_by_author_by_section)
            else:
                error_msg = "No data returned from GitHub API"
                self.error.emit(error_msg)

        except Exception as e:
            if not self._shutdown:  # Only emit error if not cancelled
                error_msg = f"Error refreshing data: {str(e)}"
                self.error.emit(error_msg)

    def requestInterruption(self):
        """Handle interruption request"""
        self.shutdown()
        super().requestInterruption()

    def shutdown(self):
        self._shutdown = True
