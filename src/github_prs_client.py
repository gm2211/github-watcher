import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests

from src.notifications import notify
from src.objects import PullRequest, TimelineEvent

DATE_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


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
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

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
            print(f"Error fetching PRs for user {user}: {e}")
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

                print(
                    f"\nDebug - Processing {len(data['items'])} items from GitHub API"
                )

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

                        print(
                            f"\nDebug - Processing PR #{item.get('number')} from {repo_owner}/{repo_name}"
                        )

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
                        print(f"Debug - Attempting to parse PR with data: {item}")
                        pr = PullRequest.parse_pr(item)
                        results.append(pr)
                        print(f"Debug - Successfully parsed PR #{pr.number}")

                    except Exception as e:
                        print(f"Warning: Error parsing PR item: {e}")
                        print(f"Item data: {item}")
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

    def get_pr_data(self, users, section=None):
        """Get PR data from GitHub API with parallel processing"""
        try:
            # Define section-specific queries
            section_queries = {
                "open": "is:pr is:open",
                "review": "is:pr is:open " "review:none " "comments:0 " "-draft:true",
                "attention": (
                    "is:pr is:open " "review:changes_requested " "-draft:true"
                ),
                "closed": f"is:pr is:closed closed:>={self._recent_date()}",
            }

            # Process only requested section or all sections
            sections_to_process = [section] if section else section_queries.keys()

            results = {}
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for section_name in sections_to_process:
                    if section_name not in section_queries:
                        continue

                    query = section_queries[section_name]
                    print(f"\nDebug - Processing {section_name} with query: {query}")

                    # Fetch PRs for all users in parallel
                    futures = [
                        executor.submit(self._fetch_user_prs, user, query, 100)
                        for user in users
                    ]

                    section_results = {}
                    for future in futures:
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
                                pr = detail_future.result()
                                if pr:
                                    updated_prs.append(pr)

                            if updated_prs:  # Only add if we have PRs
                                section_results[user] = updated_prs

                    results[section_name] = section_results

                # Create final data structure - important to return empty dicts if no results
                data = (
                    results.get("open", {}),
                    results.get("review", {}),
                    results.get("attention", {}),
                    results.get("closed", {}),
                )

                print("\nDebug - Final results:")
                print(f"Open PRs: {len(results.get('open', {}))} users")
                for user, prs in results.get("open", {}).items():
                    print(f"  {user}: {len(prs)} PRs")
                print(f"Review PRs: {len(results.get('review', {}))} users")
                print(f"Attention PRs: {len(results.get('attention', {}))} users")
                print(f"Closed PRs: {len(results.get('closed', {}))} users")

                return data

        except Exception as e:
            print(f"Error in get_pr_data: {e}")
            traceback.print_exc()
            return {}, {}, {}, {}  # Return empty dicts on error

    def _recent_date(self):
        """Get the date threshold for recently closed PRs"""
        date_threshold = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return date_threshold

    def notify_new_prs(self, new_prs):
        """Send notification for new PRs"""
        if new_prs:
            title = "New Pull Requests"
            message = f"{len(new_prs)} new PR(s) to review"
            notify(title, message)
