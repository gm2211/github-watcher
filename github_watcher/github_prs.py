from datetime import datetime, timedelta

import requests

from github_watcher.objects import PullRequest


class GitHubPRs:
    def __init__(self, token, base_url="https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get_prs(self, state="open", is_draft=None, max_results=None) -> list[PullRequest]:

        """
        Get pull requests across all accessible repositories with filtering options.

        :param state: 'open' or 'closed'
        :param is_draft: True for draft PRs, False for non-draft, None for both
        :param max_results: Maximum number of PRs to return
        :return: List of pull requests
        """
        query = f"is:pr is:{state}"
        if is_draft is not None:
            query += f" draft:{str(is_draft).lower()}"

        return self._search_issues(query, max_results)

    def get_prs(self, state="open", is_draft=None, max_results=None) -> list[PullRequest]:
        """
        Get pull requests across all accessible repositories with filtering options.

        :param state: 'open' or 'closed'
        :param is_draft: True for draft PRs, False for non-draft, None for both
        :param max_results: Maximum number of PRs to return
        :return: List of pull requests
        """
        query = f"is:pr is:{state}"
        if is_draft is not None:
            query += f" draft:{str(is_draft).lower()}"

        return self._search_issues(query, max_results)

    def get_recently_closed_prs_by_users(self, users, days=7, max_results=None):
        """
        Get recently closed PRs for specific users across all accessible repositories.

        :param users: List of usernames
        :param days: Number of days to look back
        :param max_results: Maximum number of PRs to return
        :return: List of recently closed PRs by specified users
        """
        date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        user_query = " ".join(f"author:{user}" for user in users)
        query = f"is:pr is:closed closed:>={date_threshold} {user_query}"

        return self._search_issues(query, max_results)

    def get_prs_that_await_review(self, max_results=None):
        """
        Get PRs that need review based on review status across all accessible repositories.

        :param max_results: Maximum number of PRs to return
        :return: List of PRs awaiting review
        """
        query = "is:pr is:open review:none"
        return self._search_issues(query, max_results)

    def get_prs_that_need_attention(self, days_inactive=7, max_results=None) -> list[PullRequest]:
        """
        Get PRs that have been open for a while without much activity across all accessible repositories.

        :param days_inactive: Number of days of inactivity to consider
        :param max_results: Maximum number of PRs to return
        :return: List of PRs needing attention
        """
        date_threshold = (datetime.now() - timedelta(days=days_inactive)).strftime("%Y-%m-%d")
        query = f"is:pr is:open updated:<={date_threshold}"
        return self._search_issues(query, max_results)

    def _search_issues(self, query, max_results=None) -> list[PullRequest]:

        """
        Search issues and pull requests using the given query.

        :param query: Search query string
        :param max_results: Maximum number of results to return
        :return: List of matching pull requests
        """

        endpoint = "/search/issues"
        params = {"q": query, "per_page": 100}
        results = []

        while True:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            results.extend(PullRequest.parse_prs(data['items']))

            if max_results and len(results) >= max_results:
                return results[:max_results]

            if 'next' not in response.links:
                break

            params['page'] = response.links['next']['url'].split('page=')[-1]

        return results
