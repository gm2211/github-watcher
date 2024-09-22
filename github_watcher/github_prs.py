from datetime import datetime, timedelta

import requests

from cache import Cache
from github_watcher.objects import PRState, PullRequest, TimelineEvent

DATE_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


class GitHubPRs:
    def __init__(
            self,
            token,
            base_url="https://api.github.com",
            recency_threshold=timedelta(days=1),
            cache_dir=".cache"
    ):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.recency_threshold = recency_threshold
        self.cache = Cache(cache_dir)

    def get_prs(
            self,
            state: PRState = None,
            is_draft=False,
            users=None,
            max_results=100
    ) -> dict[str, list[PullRequest]]:
        """
        Get pull requests across all accessible repositories with filtering options.

        :param state: PRState.OPEN, PRState.CLOSED, or None for both
        :param is_draft: True for draft PRs, False for non-draft, None for both
        :param users: List of usernames to filter by
        :param max_results: Maximum number of PRs to return per user
        :return: Dictionary of users and their respective pull requests
        """
        if users is None:
            users = []
        query = "is:pr"
        if state:
            query += f" is:{state.value}"
        if is_draft is not None:
            query += f" draft:{str(is_draft).lower()}"

        cache_key = f"prs_{state}_{is_draft}_{'-'.join(sorted(users))}_{max_results}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._search_issues_by_users(query, users, max_results)
        self.cache.set(cache_key, result)
        return result

    def get_recently_closed_prs_by_users(self, users, max_results=None) -> dict[str, list[PullRequest]]:
        """
        Get recently closed PRs for specific users across all accessible repositories.

        :param users: List of usernames
        :param max_results: Maximum number of PRs to return per user
        :return: Dictionary of users and their recently closed PRs
        """
        date_threshold = (datetime.now() - self.recency_threshold).strftime("%Y-%m-%d")
        query = f"is:pr is:closed closed:>={date_threshold}"

        cache_key = f"recently_closed_prs_{'-'.join(sorted(users))}_{max_results}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._search_issues_by_users(query, users, max_results)
        self.cache.set(cache_key, result)
        return result

    def get_prs_that_await_review(self, users=None, max_results=None) -> dict[str, list[PullRequest]]:
        """
        Get PRs that need review based on review status across all accessible repositories.

        :param users: List of usernames to filter by
        :param max_results: Maximum number of PRs to return per user
        :return: Dictionary of users and their PRs awaiting review
        """
        query = "is:pr is:open review:none"

        cache_key = f"await_review_prs_{'-'.join(sorted(users) if users else [])}_{max_results}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._search_issues_by_users(query, users, max_results)
        self.cache.set(cache_key, result)
        return result

    def get_prs_that_need_attention(
            self, users=None, max_results=None
    ) -> dict[str, list[PullRequest]]:
        """
        Get PRs that have been open for a while without much activity or newly created non-draft PRs across all
        accessible repositories.

        :param users: List of usernames to filter by
        :param max_results: Maximum number of PRs to return per user
        :return: Dictionary of users and their PRs needing attention
        """
        not_recently_updated = f"updated:<={self._recently_upper_bound()}"
        recently_created = f"created:>={self._recently_lower_bound()}"
        is_not_draft = "-is:draft"
        query = f"is:pr is:open ({not_recently_updated} OR  {recently_created}) {is_not_draft}))"

        cache_key = f"need_attention_prs_{'-'.join(sorted(users) if users else [])}_{max_results}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._search_issues_by_users(query, users, max_results)
        self.cache.set(cache_key, result)
        return result

    def get_pr_timeline(self, repo_owner, repo_name, pr_number):
        """
        Fetch the timeline of a specific Pull Request.

        :param repo_owner: Owner of the repository
        :param repo_name: Name of the repository
        :param pr_number: Number of the Pull Request
        :return: List of TimelineEvent objects
        """
        cache_key = f"timeline_{repo_owner}_{repo_name}_{pr_number}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        endpoint = f"/repos/{repo_owner}/{repo_name}/issues/{pr_number}/timeline"
        params = {"per_page": 100}
        events = []

        while True:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            events.extend(TimelineEvent.parse_events(data))

            if 'next' not in response.links:
                break

            params['page'] = response.links['next']['url'].split('page=')[-1]

        self.cache.set(cache_key, events)
        return events

    def _search_issues_by_users(self, base_query, users=None, max_results=None) -> dict[str, list[PullRequest]]:
        """
        Search issues and pull requests using the given query, grouped by users.

        :param base_query: Base search query string
        :param users: List of usernames to filter by
        :param max_results: Maximum number of results to return per user
        :return: Dictionary of users and their matching pull requests
        """
        results = {}

        if users:
            for user in users:
                query = f"{base_query} author:{user}"
                user_results = self._search_issues(query, max_results)
                results[user] = user_results
        else:
            all_results = self._search_issues(base_query, max_results)
            for pr in all_results:
                user = pr.user
                if user not in results:
                    results[user] = []
                results[user].append(pr)

        return results

    def _search_issues(self, query, max_results=None) -> list[PullRequest]:
        """
        Search issues and pull requests using the given query.

        :param query: Search query string
        :param max_results: Maximum number of results to return
        :return: List of matching pull requests
        """
        cache_key = f"search_{query}_{max_results}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return [PullRequest.parse_pr(pr_data) for pr_data in cached_result]

        endpoint = "/search/issues"
        params = {"q": query, "per_page": 100}
        results = []

        while True:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            results.extend(PullRequest.parse_prs(data['items']))

            if max_results and len(results) >= max_results:
                results = results[:max_results]
                break

            if 'next' not in response.links:
                break

            params['page'] = response.links['next']['url'].split('page=')[-1]

        self.cache.set(cache_key, [pr.to_dict() for pr in results])
        return results

    def _recently_lower_bound(self):
        date_threshold = (datetime.now() - self.recency_threshold).strftime(DATE_TIME_FMT)
        return date_threshold

    def _recently_upper_bound(self):
        date_threshold = (datetime.now() + self.recency_threshold).strftime(DATE_TIME_FMT)
        return date_threshold
