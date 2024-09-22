# main.py

import os
from notifications import notify, NOTIFIER_APP
from github_prs import get_user_prs


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
            prs = get_user_prs(username)
            if prs:
                pr_count = len(prs)
                notify(NOTIFIER_APP, "GitHub PRs", f"{username} has {pr_count} open pull requests.")
            else:
                notify(NOTIFIER_APP, "GitHub PRs", f"Failed to fetch PRs for {username}.")
