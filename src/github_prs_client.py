import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto

import requests

from src.notifications import notify
from src.objects import PullRequest, TimelineEvent

DATE_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


class PRSection(Enum):
    OPEN = auto()
    REVIEW = auto()
    ATTENTION = auto()
    CLOSED = auto()


@dataclass
class PRQueryConfig:
    query: str
    section: PRSection


class GitHubPRsClient:
    def __init__(
        self,
        github_token,
        recency_threshold=timedelta(days=1),
        max_workers=4,
    ):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.recency_threshold = recency_threshold
        self.max_workers = max_workers
        self._executor = None
        self._shutdown = False

        # Define section-specific queries
        self.section_queries = {
            PRSection.OPEN: PRQueryConfig(
                query="is:pr is:open", section=PRSection.OPEN
            ),
            PRSection.REVIEW: PRQueryConfig(
                query="is:pr is:open review:none comments:0 -draft:true",
                section=PRSection.REVIEW,
            ),
            PRSection.ATTENTION: PRQueryConfig(
                query="is:pr is:open review:changes_requested -draft:true",
                section=PRSection.ATTENTION,
            ),
            PRSection.CLOSED: PRQueryConfig(
                query=f"is:pr is:closed closed:>={self._recent_date()}",
                section=PRSection.CLOSED,
            ),
        }

    def get_pr_timeline(self, repo_owner, repo_name, pr_number) -> list[TimelineEvent]:
        """Fetch the timeline of a specific Pull Request."""
        endpoint = f"/repos/{repo_owner}/{repo_name}/issues/{pr_number}/timeline"
        params = {"per_page": 100}
        events = []

        while True:
            response = requests.get(
                f"{self.base_url}{endpoint}", headers=self.headers, params=params
            )
            response.raise_for_status()
            data = response.json()
            events.extend(TimelineEvent.parse_events(data))

            if "next" not in response.links:
                break

            params["page"] = response.links["next"]["url"].split("page=")[-1]

        return events

    def _fetch_user_prs(self, user, query, max_results):
        """Helper method to fetch PRs for a single user"""
        try:
            user_query = f"{query} author:{user}"
            results = self._search_issues(user_query, max_results)
            return user, results
        except Exception as e:
            print(f"Error fetching PRs for {user}: {e}")
            return user, []

    def _search_issues(self, query, max_results=None) -> list[PullRequest]:
        """Search issues and pull requests using the given query."""
        endpoint = "/search/issues"
        params = {"q": query, "per_page": 100}
        results = []

        try:
            while True:
                response = requests.get(
                    f"{self.base_url}{endpoint}", headers=self.headers, params=params
                )
                response.raise_for_status()
                data = response.json()

                # Process each PR item
                for item in data["items"]:
                    try:
                        # Extract repo owner and name from repository_url or html_url
                        if "repository_url" in item:
                            repo_parts = item["repository_url"].split("/")
                            repo_owner = repo_parts[-2]
                            repo_name = repo_parts[-1]
                        else:
                            repo_parts = item["html_url"].split("/")
                            repo_owner = repo_parts[-4]
                            repo_name = repo_parts[-3]

                        # Add repo info to item
                        item["repo_owner"] = repo_owner
                        item["repo_name"] = repo_name

                        # Ensure state is present
                        if "state" not in item:
                            item["state"] = "unknown"

                        # Convert datetime strings to proper format
                        for date_field in [
                            "created_at",
                            "updated_at",
                            "closed_at",
                            "merged_at",
                        ]:
                            if date_val := item.get(date_field):
                                try:
                                    if isinstance(date_val, str):
                                        if date_val.endswith("Z"):
                                            date_val = date_val[:-1] + "+00:00"
                                        item[date_field] = date_val
                                    elif isinstance(date_val, datetime):
                                        item[date_field] = date_val.isoformat()
                                    else:
                                        item[date_field] = str(date_val)
                                except Exception as e:
                                    print(
                                        f"Warning: Error parsing date {date_field}: {e} "
                                        f"(value: {date_val},"
                                        f" type: {type(date_val)})"
                                    )
                                    item[date_field] = None

                        # Parse PR

                        pr = PullRequest.parse_pr(item)
                        results.append(pr)

                    except Exception as e:
                        print(f"Warning: Error parsing PR item: {e}")
                        continue

                if max_results and len(results) >= max_results:
                    results = results[:max_results]
                    break

                if "next" not in response.links:
                    break

                params["page"] = response.links["next"]["url"].split("page=")[-1]

            return results

        except Exception as e:
            print(f"Error in _search_issues: {e}")
            return []

    def get_pr_details(self, repo_owner, repo_name, pr_number):
        """Get detailed PR information including file changes"""
        endpoint = f"/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
        response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
        response.raise_for_status()
        data = response.json()

        # Convert datetime strings to proper format
        for date_field in ["created_at", "updated_at", "closed_at", "merged_at"]:
            if date_val := data.get(date_field):
                try:
                    if isinstance(date_val, datetime):
                        data[date_field] = date_val.isoformat()
                    elif isinstance(date_val, str):
                        if date_val.endswith("Z"):
                            date_val = date_val[:-1] + "+00:00"
                        data[date_field] = date_val
                    else:
                        data[date_field] = str(date_val)
                except Exception as e:
                    print(
                        f"Warning: Error parsing date {date_field}: {e} (value: {date_val}, type: {type(date_val)})"
                    )
                    data[date_field] = None

        # Add repo info if not present
        if "repo_owner" not in data:
            data["repo_owner"] = repo_owner
        if "repo_name" not in data:
            data["repo_name"] = repo_name

        return data

    def _fetch_pr_details(self, pr):
        """Helper method to fetch details for a single PR"""
        try:
            details = self.get_pr_details(pr.repo_owner, pr.repo_name, pr.number)
            if details:
                pr.changed_files = details.get("changed_files")
                pr.additions = details.get("additions")
                pr.deletions = details.get("deletions")
            return pr
        except Exception as e:
            print(f"Warning: Error fetching details for PR #{pr.number}: {e}")
            return pr

    def get_pr_data(self, users, section: PRSection = None):
        """Get PR data from GitHub API with parallel processing"""
        if self._shutdown:
            print("Client is shutting down, aborting PR data fetch")
            return {}, {}, {}, {}

        try:
            # Process only requested section or all sections
            sections_to_process = [section] if section else self.section_queries.keys()

            results = {}
            for section in sections_to_process:
                query_config = self.section_queries[section]
                results[section] = self._fetch_section_data(users, query_config)

            # Create final data structure
            return (
                results.get(PRSection.OPEN, {}),
                results.get(PRSection.REVIEW, {}),
                results.get(PRSection.ATTENTION, {}),
                results.get(PRSection.CLOSED, {}),
            )

        except Exception as e:
            print(f"Error in get_pr_data: {e}")
            traceback.print_exc()
            return {}, {}, {}, {}

    def _fetch_section_data(self, users, query_config: PRQueryConfig):
        """Fetch PR data for a specific section"""
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Fetch PRs for all users in parallel
                futures = [
                    executor.submit(self._fetch_user_prs, user, query_config.query, 100)
                    for user in users
                ]

                section_results = {}
                for future in futures:
                    if self._shutdown:
                        break
                    user, user_prs = future.result()
                    if user_prs:
                        # Fetch PR details in parallel
                        detail_futures = [
                            executor.submit(self._fetch_pr_details, pr)
                            for pr in user_prs
                        ]

                        # Update PRs with details as they complete
                        updated_prs = []
                        for detail_future in detail_futures:
                            if self._shutdown:
                                break
                            pr = detail_future.result()
                            if pr:
                                updated_prs.append(pr)

                        if updated_prs:  # Only add if we have PRs
                            section_results[user] = updated_prs

                return section_results

        except Exception as e:
            print(f"Error fetching section data: {e}")
            return {}

    @staticmethod
    def _recent_date():
        """Get the date threshold for recently closed PRs"""
        date_threshold = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return date_threshold

    @staticmethod
    def notify_new_prs(new_prs):
        """Send notification for new PRs"""
        if new_prs:
            title = "New Pull Requests"
            message = f"{len(new_prs)} new PR(s) to review"
            notify(title, message)
