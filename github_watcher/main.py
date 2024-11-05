from utils import read_users_from_file, get_cached_pr_data_with_github_prs
from ui import open_ui, load_settings
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from datetime import timedelta
from PyQt6.QtWidgets import QApplication
import sys


def main():
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Ensure settings exist
    settings = load_settings()  # This will create default settings if missing
    
    users = read_users_from_file()
    if not users:
        # Still open the UI even with no users - they can add them in settings
        window = open_ui({}, {}, {}, {})
        return app.exec()

    try:
        # Create GitHubPRs instance
        github_token = get_github_api_key()
        cache_duration = settings.get('cache_duration', 1)
        github_prs = GitHubPRs(
            github_token,
            recency_threshold=timedelta(days=1),
            cache_dir=".cache",
            cache_ttl=timedelta(hours=cache_duration)
        )

        print("\nDebug - Loading initial data...")
        # Try cache first
        initial_data = github_prs.get_pr_data(users, force_refresh=False)
        
        if not initial_data:
            print("Debug - No cached data, fetching fresh data...")
            initial_data = github_prs.get_pr_data(users, force_refresh=True)
            
        if not initial_data:
            print("Debug - No data available, using empty state")
            initial_data = ({}, {}, {}, {})

        # Open UI with initial data
        window = open_ui(
            *initial_data,
            github_prs=github_prs,
            settings=settings
        )
        
        return app.exec()

    except Exception as e:
        print(f"Error fetching PR data: {e}")
        print("Please check your GitHub token and internet connection.")
        # Still open UI so they can configure settings
        window = open_ui({}, {}, {}, {})
        return app.exec()


if __name__ == "__main__":
    sys.exit(main())
