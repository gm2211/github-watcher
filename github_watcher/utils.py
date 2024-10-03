import os
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from objects import PRState


def read_users_from_file():
    file_path = os.getenv("GITHUB_USERS_FILE")
    if not file_path:
        # Fallback: use 'users.txt' in the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(project_root, "users.txt")
        print(
            f"GITHUB_USERS_FILE environment variable not set. Using default: {file_path}"
        )
    else:
        print(f"Reading users from file: {file_path}")

    try:
        with open(file_path, "r") as file:
            return [
                line.strip()
                for line in file
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        print(f"Users file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading users file: {e}")
        return []


def get_pr_data(users):
    github_token = get_github_api_key()
    github_prs = GitHubPRs(github_token)

    open_prs_by_user = github_prs.get_prs(
        state=PRState.OPEN, is_draft=False, max_results=100, users=users
    )
    prs_awaiting_review_by_user = github_prs.get_prs_that_await_review(
        max_results=50, users=users
    )
    prs_that_need_attention_by_user = github_prs.get_prs_that_need_attention(
        max_results=75, users=users
    )
    user_recently_closed_prs_by_user = github_prs.get_recently_closed_prs_by_users(
        users, max_results=100
    )

    return (
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    )
