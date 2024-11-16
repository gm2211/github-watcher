import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import auto, Enum
from typing import Dict, List, Tuple

import requests

from github_pr_watcher.notifications import notify
from github_pr_watcher.objects import PullRequest, TimelineEvent
from github_pr_watcher.settings import Settings
from github_pr_watcher.utils import parse_datetime


class PRSection(Enum):
    OPEN = auto()
    NEEDS_REVIEW = auto()
    CHANGED_REQUESTED = auto()
    CLOSED = auto()


@dataclass
class PRQueryConfig:
    query: str


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
            PRSection.OPEN: PRQueryConfig(query="is:pr is:open"),
            # TODO instead of comments:0 we should look at the last comment date
            PRSection.NEEDS_REVIEW: PRQueryConfig(
                query="is:pr is:open review:none comments:0 -draft:true"
            ),
            PRSection.CHANGED_REQUESTED: PRQueryConfig(
                query="is:pr is:open review:changes_requested -draft:true"
            ),
            PRSection.CLOSED: PRQueryConfig(
                query=f"is:pr is:closed closed:>={self._recent_date()}"
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

    def _search_for_user_prs(self, user, query, max_results):
        """Helper method to fetch PRs for a single user"""
        try:
            user_query = f"{query} author:{user}"
            results = self._search_prs(user_query, max_results)
            return user, results
        except Exception as e:
            print(f"Error fetching PRs for {user}: {e}")
            traceback.print_exc()
            return user, []

    def _search_prs(self, query, max_results=None) -> list[PullRequest]:
        """Search issues and pull requests using the given query - we assume all matching issues are PRs."""
        endpoint = "/search/issues"
        params = {"q": query, "per_page": 100}
        results = []

        try:
            while True:
                response = requests.get(
                    f"{self.base_url}{endpoint}", headers=self.headers, params=params
                )
                if response.status_code != 200:
                    print(f"Error in _search_issues: {response.text}")
                    return []
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
                                    traceback.print_exc()
                                    item[date_field] = None

                        # Parse PR

                        pr = PullRequest.parse_pr(item)
                        results.append(pr)

                    except Exception as e:
                        print(f"Warning: Error parsing PR item: {e}")
                        traceback.print_exc()
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
            traceback.print_exc()
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
                    traceback.print_exc()
                    data[date_field] = None

        # Add repo info if not present
        if "repo_owner" not in data:
            data["repo_owner"] = repo_owner
        if "repo_name" not in data:
            data["repo_name"] = repo_name

        return data

    def _fetch_and_enrich_with_pr_details(self, pr: PullRequest) -> (PullRequest, bool):
        """Helper method to fetch details for a single PR"""
        try:
            # Get repository details first
            repo_url = f"{self.base_url}/repos/{pr.repo_owner}/{pr.repo_name}"
            repo_response = requests.get(repo_url, headers=self.headers)
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                pr.archived = repo_data.get("archived", False)

            # Get basic PR details
            details = self.get_pr_details(pr.repo_owner, pr.repo_name, pr.number)
            if details:
                pr.changed_files = details.get("changed_files")
                pr.additions = details.get("additions")
                pr.deletions = details.get("deletions")
                pr.merged_at = parse_datetime(details.get("merged_at"))
                pr.merged = details.get("merged", False)
                pr.merged_by = (
                    details.get("merged_by", {}).get("login")
                    if details.get("merged_by")
                    else None
                )

            # Get comments and reviews
            comments_url = f"{self.base_url}/repos/{pr.repo_owner}/{pr.repo_name}/issues/{pr.number}/comments"
            reviews_url = f"{self.base_url}/repos/{pr.repo_owner}/{pr.repo_name}/pulls/{pr.number}/reviews"

            # Fetch comments and reviews in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                comments_future = executor.submit(
                    requests.get, comments_url, headers=self.headers
                )
                reviews_future = executor.submit(
                    requests.get, reviews_url, headers=self.headers
                )

                comments_response = comments_future.result()
                reviews_response = reviews_future.result()

            comments = (
                comments_response.json() if comments_response.status_code == 200 else []
            )
            reviews = (
                reviews_response.json() if reviews_response.status_code == 200 else []
            )

            # Process comments
            comment_count_by_author = {}
            last_comment_time = None
            last_comment_author = None

            for comment in sorted(comments, key=lambda x: x["created_at"]):
                author = comment["user"]["login"]
                comment_count_by_author[author] = (
                    comment_count_by_author.get(author, 0) + 1
                )

                comment_time = parse_datetime(comment["created_at"])
                if last_comment_time is None or comment_time > last_comment_time:
                    last_comment_time = comment_time
                    last_comment_author = author

            # Process reviews
            approved_by = set()
            latest_reviews = {}  # Track latest review by each reviewer
            for review in reviews:
                reviewer = review["user"]["login"]
                review_time = parse_datetime(review["submitted_at"])

                # Update latest review for this reviewer
                if (
                    reviewer not in latest_reviews
                    or review_time > latest_reviews[reviewer][0]
                ):
                    latest_reviews[reviewer] = (review_time, review["state"].lower())

                # Track approvals
                if review["state"].lower() == "approved":
                    approved_by.add(reviewer)

            # Add new attributes to PR
            pr.comment_count_by_author = comment_count_by_author
            pr.last_comment_time = last_comment_time
            pr.last_comment_author = last_comment_author
            pr.approved_by = list(approved_by)
            pr.latest_reviews = {
                reviewer: state for reviewer, (_, state) in latest_reviews.items()
            }

            return pr, False

        except Exception as e:
            print(f"Warning: Error fetching details for PR #{pr.number}: {e}")
            traceback.print_exc()
            # Set default values on error
            pr.comment_count_by_author = {}
            pr.last_comment_time = None
            pr.last_comment_author = None
            pr.approved_by = []
            pr.latest_reviews = {}
            pr.merged = False
            pr.merged_by = None
            return pr, True

    def get_pr_data(
        self, users: List[str], section: PRSection = None, settings: Settings = None
    ) -> Dict[PRSection, Dict[str, List[Tuple[PullRequest, bool]]]]:
        """Get PR data from GitHub API with parallel processing"""
        if self._shutdown:
            return {}

        try:
            # Process only requested section or all sections
            sections_to_process = [section] if section else self.section_queries.keys()

            # Update the CLOSED query with current threshold if settings provided
            if settings:
                recent_days = settings.thresholds.recently_closed_days
                self.section_queries[PRSection.CLOSED] = PRQueryConfig(
                    query=f"is:pr is:closed closed:>={self._recent_date(recent_days)}"
                )

            prs_by_author_by_section = {}
            for section in sections_to_process:
                query_config = self.section_queries[section]
                prs_by_author_by_section[section] = self._fetch_prs_by_author(
                    users, query_config
                )

            return prs_by_author_by_section

        except Exception as e:
            print(f"Error in get_pr_data: {e}")
            traceback.print_exc()
            return {}

    def _fetch_prs_by_author(
        self, users, query_config: PRQueryConfig
    ) -> Dict[str, List[Tuple[PullRequest, bool]]]:
        """Fetch PR data for a specific section"""
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Fetch PRs for all users in parallel
                futures = [
                    executor.submit(
                        self._search_for_user_prs, user, query_config.query, 100
                    )
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
                            executor.submit(self._fetch_and_enrich_with_pr_details, pr)
                            for pr in user_prs
                        ]

                        # Update PRs with details as they complete
                        prs_with_details = []
                        for detail_future in detail_futures:
                            if self._shutdown:
                                break
                            pr_with_details, partial = detail_future.result()
                            if pr_with_details:
                                prs_with_details.append((pr_with_details, partial))

                        if prs_with_details:  # Only add if we have PRs
                            section_results[user] = prs_with_details

                return section_results

        except RuntimeError("cannot schedule new futures after shutdown"):
            return {}
        except Exception as e:
            print(f"Error fetching section data: {e}")
            traceback.print_exc()
            return {}

    @staticmethod
    def _recent_date(days=7):
        """Get the date threshold for recently closed PRs"""
        date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return date_threshold

    @staticmethod
    def notify_new_prs(new_prs):
        """Send notification for new PRs"""
        if new_prs:
            title = "New Pull Requests"
            message = f"{len(new_prs)} new PR(s) to review"
            notify(title, message)
