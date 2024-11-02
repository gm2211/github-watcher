from utils import read_users_from_file, get_pr_data
from ui import open_ui


def main():
    users = read_users_from_file()
    if not users:
        print(
            "No users found. Please check your GITHUB_USERS_FILE or create a users.txt file in the project root."
        )
        return

    try:
        (
            open_prs_by_user,
            prs_awaiting_review_by_user,
            prs_that_need_attention_by_user,
            user_recently_closed_prs_by_user,
        ) = get_pr_data(users)
    except Exception as e:
        print(f"Error fetching PR data: {e}")
        print("Please check your GitHub token and internet connection.")
        return

    # Add these debug prints:
    print("\nNeeds Review PRs:")
    print(prs_awaiting_review_by_user)
    print("\nChanges Requested PRs:")
    print(prs_that_need_attention_by_user)
    print("\nOpen PRs:")
    print(open_prs_by_user)

    # Open the UI and pass the pull requests data
    open_ui(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user,
    )


if __name__ == "__main__":
    main()
