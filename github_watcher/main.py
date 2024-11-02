from utils import read_users_from_file, get_cached_pr_data_with_github_prs
from ui import open_ui, load_settings
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from datetime import timedelta
from PyQt6.QtCore import QTimer


def main():
    # Ensure settings exist
    settings = load_settings()
    users = read_users_from_file()
    
    # Create GitHubPRs instance
    github_token = get_github_api_key()
    cache_duration = settings.get('cache_duration', 1)
    github_prs = GitHubPRs(
        github_token,
        recency_threshold=timedelta(days=1),
        cache_dir=".cache",
        cache_ttl=timedelta(hours=cache_duration)
    )

    # Try to get cached data quickly
    initial_data = ({}, {}, {}, {})  # Empty data to start with
    try:
        print("Checking cache...")
        cached_data = get_cached_pr_data_with_github_prs(users)
        if cached_data and all(cached_data):
            print("Using cached data for initial display")
            initial_data = cached_data
    except Exception as e:
        print(f"Error loading cache: {e}")

    # Open UI immediately with either cached data or empty state
    window = open_ui(
        *initial_data,
        github_prs=github_prs,
        settings=settings
    )

    # If we didn't get cached data, trigger a refresh after UI is shown
    if not any(initial_data):
        # Use QTimer to trigger refresh after UI is shown
        QTimer.singleShot(100, window.refresh_data)

    return window.exec()


if __name__ == "__main__":
    main()
