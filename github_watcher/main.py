import os

from github_auth import get_github_api_key
from github_prs import GitHubPRs
from notifications import NOTIFIER_APP, notify
from objects import PullRequest


def read_users_from_file():
    file_path = os.getenv('GITHUB_USERS_FILE')
    if not file_path:
        print("GITHUB_USERS_FILE environment variable not set.")
        return []

    print(f"Reading users from file: {file_path}")
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Users file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading users file: {e}")
        return []


if __name__ == "__main__":
    users = read_users_from_file()

    if not users:
        print("No users found. Please check your GITHUB_USERS_FILE.")
    else:
        for username in users:
            github_token = get_github_api_key()
            github_prs: GitHubPRs = GitHubPRs(github_token)

            # Get open, non-draft PRs across all repos (max 100 PRs)
            open_prs = github_prs.get_prs(state="open", is_draft=False, max_results=100)

            # Get recently closed PRs by specific users (max 100 PRs)
            closed_prs = github_prs.get_recently_closed_prs_by_users([username], max_results=100)

            # Get PRs awaiting review (max 50 PRs)
            awaiting_review = github_prs.get_prs_that_await_review(max_results=50)

            # Get PRs needing attention (max 75 PRs)
            need_attention = github_prs.get_prs_that_need_attention(max_results=75)
            pr: PullRequest
            for pr in need_attention:
                notify(NOTIFIER_APP, "GitHub PRs", f"{pr.number} for {username} needs attention.")
