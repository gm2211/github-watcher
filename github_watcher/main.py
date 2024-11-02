from utils import read_users_from_file, get_pr_data
from ui import open_ui, load_settings


def main():
    # Ensure settings exist
    settings = load_settings()  # This will create default settings if missing
    
    users = read_users_from_file()
    if not users:
        # Still open the UI even with no users - they can add them in settings
        open_ui({}, {}, {}, {})
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
