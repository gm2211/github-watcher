import requests
from github_auth import get_github_api_key


def get_user_prs(username):
    api_key = get_github_api_key()
    headers = {
        'Authorization': f'token {api_key}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/search/issues?q=author:{username}+is:pr'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        prs = response.json()['items']
        return prs
    else:
        print(f"Failed to fetch PRs. Status code: {response.status_code}")
        return None


if __name__ == "__main__":
    username = "gm2211"
    prs = get_user_prs(username)

    if prs:
        print(f"Pull Requests for {username}:")
        for pr in prs:
            print(f"- {pr['title']} ({pr['html_url']})")
    else:
        print("No PRs found or there was an error fetching PRs.")
