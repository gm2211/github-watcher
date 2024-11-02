from utils import read_users_from_file, get_cached_pr_data_with_github_prs
from ui import open_ui, load_settings
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from datetime import timedelta


def main():
    # Ensure settings exist
    settings = load_settings()  # This will create default settings if missing
    
    users = read_users_from_file()
    if not users:
        # Still open the UI even with no users - they can add them in settings
        open_ui({}, {}, {}, {})
        return

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

        print("\nDebug - Trying to load data from cache...")
        cached_data = get_cached_pr_data_with_github_prs(users)
        
        if cached_data:
            print("Debug - Using cached data for initial display")
            (
                open_prs_by_user,
                prs_awaiting_review_by_user,
                prs_that_need_attention_by_user,
                user_recently_closed_prs_by_user,
            ) = cached_data
        else:
            print("Debug - No valid cache found, fetching fresh data...")
            (
                open_prs_by_user,
                prs_awaiting_review_by_user,
                prs_that_need_attention_by_user,
                user_recently_closed_prs_by_user,
            ) = github_prs.get_pr_data(users)
            
    except Exception as e:
        print(f"Error fetching PR data: {e}")
        print("Please check your GitHub token and internet connection.")
        # Still open UI so they can configure settings
        open_ui({}, {}, {}, {})
        return

    # Open the UI and pass the pull requests data
    open_ui(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    )


if __name__ == "__main__":
    main()
