import os

from github_auth import get_github_api_key
from github_prs import GitHubPRs
from notifications import NOTIFIER_APP, notify
from objects import PRState, PullRequest


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
        github_token = get_github_api_key()
        github_prs: GitHubPRs = GitHubPRs(github_token)

        # Get PR information for all users in one call per PR type
        user_open_prs = github_prs.get_prs(
            state=PRState.OPEN,
            is_draft=False,
            max_results=100,
            users=users
        )

        user_awaiting_review = github_prs.get_prs_that_await_review(max_results=50, users=users)
        prs_that_need_attention = github_prs.get_prs_that_need_attention(max_results=75, users=users)
        user_recently_closed_prs = github_prs.get_recently_closed_prs_by_users(users, max_results=100)

        # Iterate through users to send notifications
        for username in users:
            print(user_open_prs)
            print(prs_that_need_attention)
            if username in prs_that_need_attention:
                for pr in prs_that_need_attention[username]:
                    notify(NOTIFIER_APP, "GitHub PRs", f"{pr.number} for {username} needs attention.")
