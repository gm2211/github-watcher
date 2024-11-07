from src.ui import load_settings


def read_users_from_file():
    settings = load_settings()
    
    if not settings or not settings.get('users'):
        print("No users configured. Please add users in Settings.")
        return []
    
    return settings.get('users', [])


def get_cached_pr_data_with_github_prs(users):
    """Helper function to create GitHubPRs instance and get cached data"""
    from github_auth import get_github_api_key
    from github_prs import GitHubPRs
    from datetime import timedelta
    
    github_token = get_github_api_key()
    settings = load_settings()
    cache_duration = settings.get('cache_duration', 1)
    
    github_prs = GitHubPRs(
        github_token,
        recency_threshold=timedelta(days=1),
        cache_dir=".cache",
        cache_ttl=timedelta(hours=cache_duration)
    )
    
    return github_prs.get_cached_data(users)
