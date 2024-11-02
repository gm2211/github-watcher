import os
from datetime import timedelta
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from objects import PRState
from ui import load_settings, save_settings


def read_users_from_file():
    # Load from settings.yaml instead of users.txt
    settings = load_settings()
    
    if not settings or not settings.get('users'):
        print("No users configured. Please add users in Settings.")
        return []
    
    return settings.get('users', [])


def get_pr_data(users):
    github_token = get_github_api_key()
    
    # Load cache settings from settings.yaml
    settings = load_settings()
    cache_duration = settings.get('cache_duration', 1)  # Default 1 hour if not set
    
    # Create GitHubPRs with settings from settings.yaml
    github_prs = GitHubPRs(
        github_token,
        recency_threshold=timedelta(days=1),
        cache_dir=".cache",
        cache_ttl=timedelta(hours=cache_duration)  # Use configured cache duration
    )

    # Invalidate state-related caches before fetching
    github_prs.cache.invalidate_bucket("search_issues")

    print("\nDebug - Fetching PR data from GitHub API...")
    
    # Get the basic PR data
    open_prs_by_user = github_prs.get_prs(
        state=PRState.OPEN, is_draft=False, max_results=100, users=users
    )
    print("\nDebug - Open PRs fetched:", open_prs_by_user)
    
    prs_awaiting_review_by_user = github_prs.get_prs_that_await_review(
        max_results=50, users=users
    )
    print("\nDebug - PRs awaiting review:", prs_awaiting_review_by_user)
    
    prs_that_need_attention_by_user = github_prs.get_prs_that_need_attention(
        max_results=75, users=users
    )
    
    user_recently_closed_prs_by_user = github_prs.get_recently_closed_prs_by_users(
        users, max_results=100
    )
    print("\nDebug - Recently closed PRs:", user_recently_closed_prs_by_user)

    # Enrich PRs with timeline data - this is expensive, so we can cache it
    def enrich_prs(prs_by_user):
        enriched = {}
        for user, prs in prs_by_user.items():
            enriched[user] = []
            for pr in prs:
                # Timeline data changes less frequently, so we can use cache
                timeline = github_prs.get_pr_timeline(
                    pr.repo_owner, pr.repo_name, pr.number
                )
                print(f"\nDebug - Timeline fetched for PR #{pr.number}")
                print(f"Debug - PR state: {pr.state}, merged: {pr.merged_at}")
                pr.timeline = timeline
                enriched[user].append(pr)
        return enriched

    # Enrich all PR sets with timeline data
    print("\nDebug - Enriching PR data with timelines...")
    open_prs_by_user = enrich_prs(open_prs_by_user)
    prs_awaiting_review_by_user = enrich_prs(prs_awaiting_review_by_user)
    prs_that_need_attention_by_user = enrich_prs(prs_that_need_attention_by_user)
    user_recently_closed_prs_by_user = enrich_prs(user_recently_closed_prs_by_user)

    return (
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    )
