from PyQt6.QtCore import pyqtSignal, QThread


class RefreshWorker(QThread):
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, github_prs_client, users, settings=None, section=None):
        super().__init__()
        self.github_prs_client = github_prs_client
        self.users = users
        self.settings = settings
        self.section = section

    def run(self):
        try:
            # Get PR data
            data = self.github_prs_client.get_pr_data(
                self.users, self.section, settings=self.settings
            )

            if data is not None:
                self.progress.emit("Completed refresh")
                self.finished.emit(data)
            else:
                error_msg = "No data returned from GitHub API"
                self.error.emit(error_msg)

        except Exception as e:
            error_msg = f"Error refreshing data: {str(e)}"
            self.error.emit(error_msg)
