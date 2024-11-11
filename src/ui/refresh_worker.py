from PyQt6.QtCore import pyqtSignal, QThread


class RefreshWorker(QThread):
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, github_prs_client, users, section=None):
        super().__init__()
        self.github_prs_client = github_prs_client
        self.users = users
        self.section = section

    def run(self):
        try:
            print(f"\nDebug - Worker: Starting refresh...")
            print(f"Debug - Users to fetch: {self.users}")

            # Get PR data
            data = self.github_prs_client.get_pr_data(self.users)

            if data is not None:
                print("Debug - Successfully fetched PR data")
                self.progress.emit("Completed refresh")
                self.finished.emit(data)
            else:
                error_msg = "No data returned from GitHub API"
                print(f"Debug - Error: {error_msg}")
                self.error.emit(error_msg)

        except Exception as e:
            error_msg = f"Error refreshing data: {str(e)}"
            print(f"Debug - {error_msg}")
            self.error.emit(error_msg)
