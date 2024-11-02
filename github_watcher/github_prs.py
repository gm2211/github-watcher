from datetime import datetime, timedelta
import re
import traceback

import requests

from cache import Cache, get_cached_pr_data, cache_pr_data
from objects import PRState, PullRequest, TimelineEvent, TimelineEventType

DATE_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


class GitHubPRs:
    def __init__(
            self,
            github_token,
            recency_threshold=timedelta(days=1),
            cache_dir=".cache",
            cache_ttl=timedelta(hours=1)
    ):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.recency_threshold = recency_threshold
        self.cache = Cache(cache_dir)
        self.cache_ttl = cache_ttl

    def get_prs(
            self,
            state: PRState = None,
            is_draft=False,
            users=None,
            max_results=100,
            force_refresh=False
    ) -> dict[str, list[PullRequest]]:
        """
        Get pull requests across all accessible repositories with filtering options.
        """
        print("\nDebug - get_prs called with:")
        print(f"  - state: {state}")
        print(f"  - is_draft: {is_draft}")
        print(f"  - users: {users}")
        print(f"  - max_results: {max_results}")
        print(f"  - force_refresh: {force_refresh}")
        
        if users is None:
            users = []
        
        # Build base query
        query_parts = ["is:pr"]
        if state:
            query_parts.append(f"is:{state.value}")
        if is_draft is not None:
            query_parts.append(f"draft:{str(is_draft).lower()}")
        
        # Add user query without parentheses
        if users:
            user_query = " ".join(f"author:{user}" for user in users)
            query_parts.append(user_query)
        
        query = " ".join(query_parts)
        print(f"Debug - Constructed query: {query}")
        
        # Get results directly without user filtering since it's in the query
        results = self._search_issues(query, max_results)
        
        # Organize results by user
        results_by_user = {}
        for pr in results:
            user = pr.user.login
            if user not in results_by_user:
                results_by_user[user] = []
            results_by_user[user].append(pr)
        
        return results_by_user

    def get_recently_closed_prs_by_users(self, users, max_results=None, force_refresh=False) -> dict[str, list[PullRequest]]:
        """
        Get recently closed PRs for specific users across all accessible repositories.

        :param users: List of usernames
        :param max_results: Maximum number of PRs to return per user
        :param force_refresh: If True, bypass cache and fetch fresh data
        :return: Dictionary of users and their recently closed PRs
        """
        date_threshold = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"is:pr is:closed closed:>={date_threshold}"
        
        return self._search_issues_by_users(query, users, max_results, force_refresh)

    def get_recently_merged_prs_by_users(self, users, max_results=None) -> dict[str, list[PullRequest]]:
        """
        Get recently merged PRs for specific users across all accessible repositories.

        :param users: List of usernames
        :param max_results: Maximum number of PRs to return per user
        :return: Dictionary of users and their recently merged PRs
        """
        date_threshold = (datetime.now() - self.recency_threshold).strftime("%Y-%m-%d")
        query = f"is:pr is:merged merged:>={date_threshold}"

        return self._search_issues_by_users(query, users, max_results)

    def get_prs_that_await_review(self, users=None, max_results=None, force_refresh=False) -> dict[str, list[PullRequest]]:
        query = "is:pr is:open review:none comments:0"
        return self._search_issues_by_users(query, users, max_results, force_refresh)

    def get_prs_that_need_attention(self, users=None, max_results=None, force_refresh=False) -> dict[str, list[PullRequest]]:
        """
        Get PRs that have been open for a while without much activity or newly created non-draft PRs across all
        accessible repositories.

        :param users: List of usernames to filter by
        :param max_results: Maximum number of PRs to return per user
        :param force_refresh: If True, bypass cache and fetch fresh data
        :return: Dictionary of users and their PRs needing attention
        """
        not_recently_updated = f"updated:<={self._recently_upper_bound()}"
        recently_created = f"created:>={self._recently_lower_bound()}"
        is_not_draft = "-is:draft"
        query = f"is:pr is:open ({not_recently_updated} OR  {recently_created}) {is_not_draft}))"
        return self._search_issues_by_users(query, users, max_results, force_refresh)

    def get_pr_timeline(self, repo_owner, repo_name, pr_number, force_refresh=False) -> list[TimelineEvent]:
        """
        Fetch the timeline of a specific Pull Request.
        """
        cache_key = f"timeline_{repo_owner}_{repo_name}_{pr_number}"
        bucket_name = "pr_timeline"
        
        if not force_refresh:
            cached_result = self.cache.get(cache_key, bucket_name)
            if cached_result:
                return [TimelineEvent.from_dict(event_data) for event_data in cached_result]
        
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

        self.cache.set(cache_key, [event.to_dict() for event in events], bucket_name)
        return events

    def _search_issues_by_users(self, base_query, users=None, max_results=None, force_refresh=False) -> dict[str, list[PullRequest]]:
        """Search issues by users with caching"""
        print("\nDebug - _search_issues_by_users called with:")
        print(f"  - base_query: {base_query}")
        print(f"  - users: {users}")
        print(f"  - max_results: {max_results}")
        print(f"  - force_refresh: {force_refresh}")
        
        normalized_query = self._normalize_query(base_query)
        cache_key = f"search_issues_by_users_{normalized_query}_{'-'.join(sorted(users) if users else [])}_{max_results}"
        bucket_name = "search_issues"
        
        cached_result = self.cache.get(cache_key, bucket_name)
        if not force_refresh and cached_result and self._is_cache_valid(cached_result, base_query):
            print("Debug - Using cached search results")
            return {user: [PullRequest.parse_pr(pr_data) for pr_data in prs] for user, prs in
                    cached_result['results'].items()}
        
        print("Debug - Performing fresh search")
        results = {}
        if users:
            for user in users:
                query = f"{base_query} author:{user}"
                print(f"\nDebug - Searching with query: {query}")
                user_results = self._search_issues(query, max_results)
                print(f"Debug - Found {len(user_results)} results for user {user}")
                if user_results:  # Only add user if they have results
                    results[user] = user_results
        else:
            print("\nDebug - Searching without user filter")
            all_results = self._search_issues(base_query, max_results)
            for pr in all_results:
                user = pr.user.login
                if user not in results:
                    results[user] = []
                results[user].append(pr)
        
        print(f"\nDebug - Total results by user: {', '.join(f'{user}: {len(prs)}' for user, prs in results.items())}")
        
        cache_data = {
            'results': {user: [pr.to_dict() for pr in prs] for user, prs in results.items()},
            'cache_time': datetime.now().isoformat(),
            'original_query': base_query
        }
        self.cache.set(cache_key, cache_data, bucket_name)
        return results

    @staticmethod
    def _normalize_query(query):
        """
        Normalize the query by replacing date and time-based conditions with placeholders.
        """
        # Replace date and time-based conditions with placeholders
        normalized_query = re.sub(
            r'(created|updated|closed):(>=|<=|>|<)?(\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?)',
            r'\1:DATETIME_PLACEHOLDER',
            query
        )
        return normalized_query

    def _is_cache_valid(self, cached_data, original_query):
        """
        Check if the cached data is still valid based on the original query and cache TTL.
        """
        if 'cache_time' not in cached_data:
            print("Debug - No cache_time in cached data")
            return False

        try:
            # Handle both string and datetime cache_time
            if isinstance(cached_data['cache_time'], str):
                cache_time = datetime.fromisoformat(cached_data['cache_time'])
            elif isinstance(cached_data['cache_time'], datetime):
                cache_time = cached_data['cache_time']
            else:
                print(f"Debug - Invalid cache_time type: {type(cached_data['cache_time'])}")
                return False

            if datetime.now() - cache_time > self.cache_ttl:
                print("Debug - Cache has expired")
                return False

            # Check if the query contains time-sensitive conditions
            date_conditions = re.findall(
                r'(created|updated|closed):(>=|<=|>|<)?(\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?)',
                original_query
            )
            for condition, operator, date_str, _ in date_conditions:
                try:
                    if 'T' in date_str:
                        query_datetime = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    else:
                        query_datetime = datetime.strptime(date_str, "%Y-%m-%d")

                    if operator in ('>=', '>'):
                        if datetime.now() - query_datetime > self.cache_ttl:
                            print("Debug - Query date condition invalidates cache")
                            return False
                    elif operator in ('<=', '<'):
                        if query_datetime - datetime.now() > self.cache_ttl:
                            print("Debug - Query date condition invalidates cache")
                            return False
                except ValueError as e:
                    print(f"Debug - Error parsing query date: {e}")
                    return False

            return True
            
        except Exception as e:
            print(f"Debug - Error validating cache: {e}")
            return False

    def _search_issues(self, query, max_results=None) -> list[PullRequest]:
        """
        Search issues and pull requests using the given query.
        """
        normalized_query = self._normalize_query(query)
        cache_key = f"search_{normalized_query}_{max_results}"
        bucket_name = "search_issues"

        cached_result = self.cache.get(cache_key, bucket_name)
        if cached_result and self._is_cache_valid(cached_result, query):
            return [PullRequest.parse_pr(pr_data) for pr_data in cached_result['results']]

        endpoint = "/search/issues"
        params = {"q": query, "per_page": 100}
        results = []

        while True:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            print(f"\nDebug - Processing {len(data['items'])} items from GitHub API")
            
            # Process each PR item
            for item in data['items']:
                try:
                    # Extract repo owner and name from repository_url or html_url
                    if 'repository_url' in item:
                        repo_parts = item['repository_url'].split('/')
                        repo_owner = repo_parts[-2]
                        repo_name = repo_parts[-1]
                    else:
                        repo_parts = item['html_url'].split('/')
                        repo_owner = repo_parts[-4]
                        repo_name = repo_parts[-3]
                    
                    print(f"\nDebug - Processing PR #{item.get('number')} from {repo_owner}/{repo_name}")
                    
                    # Add repo info to item
                    item['repo_owner'] = repo_owner
                    item['repo_name'] = repo_name
                    
                    # Convert datetime strings to proper format
                    for date_field in ['created_at', 'updated_at', 'closed_at', 'merged_at']:
                        if date_val := item.get(date_field):
                            try:
                                print(f"Debug - Processing {date_field}: {date_val} (type: {type(date_val)})")
                                if isinstance(date_val, str):
                                    # Handle both formats: with Z and with timezone offset
                                    if date_val.endswith('Z'):
                                        date_val = date_val[:-1] + '+00:00'
                                        print(f"Debug - Converted Z format to: {date_val}")
                                    item[date_field] = date_val
                                elif isinstance(date_val, datetime):
                                    item[date_field] = date_val.isoformat()
                                    print(f"Debug - Converted datetime to ISO: {item[date_field]}")
                                else:
                                    item[date_field] = str(date_val)
                                    print(f"Debug - Converted other type to string: {item[date_field]}")
                            except Exception as e:
                                print(f"Warning: Error parsing date {date_field}: {e} (value: {date_val}, type: {type(date_val)})")
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

            if 'next' not in response.links:
                break

            params['page'] = response.links['next']['url'].split('page=')[-1]

        print(f"\nDebug - Successfully processed {len(results)} PRs")
        
        cache_data = {
            'results': [pr.to_dict() for pr in results],
            'cache_time': datetime.now().isoformat(),
            'original_query': query
        }
        self.cache.set(cache_key, cache_data, bucket_name)
        return results

    def _recently_lower_bound(self):
        date_threshold = (datetime.now() - self.recency_threshold).strftime(DATE_TIME_FMT)
        return date_threshold

    def _recently_upper_bound(self):
        date_threshold = (datetime.now() + self.recency_threshold).strftime(DATE_TIME_FMT)
        return date_threshold

    def get_pr_details(self, repo_owner, repo_name, pr_number):
        """Get detailed PR information including file changes"""
        endpoint = f"/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
        response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        # Convert datetime strings to proper format
        for date_field in ['created_at', 'updated_at', 'closed_at', 'merged_at']:
            if date_val := data.get(date_field):
                try:
                    if isinstance(date_val, datetime):
                        data[date_field] = date_val.isoformat()
                    elif isinstance(date_val, str):
                        # Ensure it's a valid ISO format
                        if date_val.endswith('Z'):
                            date_val = date_val[:-1] + '+00:00'
                        # Validate it's a proper ISO format
                        datetime.fromisoformat(date_val)  # Just to validate
                        data[date_field] = date_val
                    else:
                        data[date_field] = str(date_val)
                except Exception as e:
                    print(f"Warning: Error parsing date {date_field}: {e} (value: {date_val}, type: {type(date_val)})")
                    data[date_field] = None
        
        # Add repo info if not present
        if 'repo_owner' not in data:
            data['repo_owner'] = repo_owner
        if 'repo_name' not in data:
            data['repo_name'] = repo_name
        
        return data

    def get_pr_data(self, users, force_refresh=False):
        """
        Get PR data from GitHub API or cache
        
        :param users: List of usernames to get PRs for
        :param force_refresh: If True, bypass cache and fetch fresh data
        :return: Tuple of PR data dictionaries
        """
        print("\nDebug - get_pr_data called with:")
        print(f"  - users: {users}")
        print(f"  - force_refresh: {force_refresh}")
        
        try:
            # Only check cache if not forcing refresh
            if not force_refresh:
                print("Debug - Checking cache...")
                cached_data = self.get_cached_data(users)
                if cached_data:
                    print("Debug - Using cached data")
                    return cached_data
            else:
                print("Debug - Bypassing cache for manual refresh")
                
            # Get the basic PR data
            print("\nDebug - Fetching open PRs...")
            open_prs_by_user = self.get_prs(
                state=PRState.OPEN, is_draft=False, max_results=100, users=users, force_refresh=force_refresh
            )
            print(f"Debug - Fetched {sum(len(prs) for prs in open_prs_by_user.values())} open PRs")
            
            # Fetch detailed PR data for each PR
            print("\nDebug - Fetching PR details...")
            for user, user_prs in open_prs_by_user.items():
                print(f"Debug - Processing {len(user_prs)} PRs for user {user}")
                for pr in user_prs:
                    try:
                        print(f"Debug - Fetching details for PR #{pr.number}")
                        detailed_pr = self.get_pr_details(pr.repo_owner, pr.repo_name, pr.number)
                        if detailed_pr:
                            pr.changed_files = detailed_pr.get('changed_files')
                            pr.additions = detailed_pr.get('additions')
                            pr.deletions = detailed_pr.get('deletions')
                            print(f"Debug - Got details: {pr.changed_files} files, +{pr.additions} -{pr.deletions}")
                    except Exception as e:
                        print(f"Warning: Error fetching details for PR #{pr.number}: {e}")
            
            print("\nDebug - Fetching PRs awaiting review...")
            prs_awaiting_review_by_user = self.get_prs_that_await_review(
                max_results=50, users=users, force_refresh=force_refresh
            )
            print(f"Debug - Fetched {sum(len(prs) for prs in prs_awaiting_review_by_user.values())} PRs awaiting review")
            
            print("\nDebug - Fetching PRs needing attention...")
            prs_that_need_attention_by_user = self.get_prs_that_need_attention(
                max_results=75, users=users, force_refresh=force_refresh
            )
            print(f"Debug - Fetched {sum(len(prs) for prs in prs_that_need_attention_by_user.values())} PRs needing attention")
            
            print("\nDebug - Fetching recently closed PRs...")
            user_recently_closed_prs_by_user = self.get_recently_closed_prs_by_users(
                users, max_results=100, force_refresh=force_refresh
            )
            print(f"Debug - Fetched {sum(len(prs) for prs in user_recently_closed_prs_by_user.values())} recently closed PRs")

            # Enrich all PR sets with timeline data
            print("\nDebug - Starting PR enrichment...")
            open_prs_by_user = self._enrich_prs_with_timeline(open_prs_by_user)
            prs_awaiting_review_by_user = self._enrich_prs_with_timeline(prs_awaiting_review_by_user)
            prs_that_need_attention_by_user = self._enrich_prs_with_timeline(prs_that_need_attention_by_user)
            user_recently_closed_prs_by_user = self._enrich_prs_with_timeline(user_recently_closed_prs_by_user)
            print("Debug - Completed PR enrichment")

            data = (
                open_prs_by_user,
                prs_awaiting_review_by_user,
                prs_that_need_attention_by_user,
                user_recently_closed_prs_by_user,
            )

            # Only cache if data was successfully fetched
            if any(data):
                print("\nDebug - Caching fresh data")
                self.cache_data(users, data)
            else:
                print("\nDebug - No data to cache")

            return data
            
        except Exception as e:
            print(f"\nError in get_pr_data: {e}")
            print("Debug - Stack trace:")
            traceback.print_exc()  # Print the full stack trace
            if not force_refresh:
                # Only try cache on error if not forcing refresh
                print("Debug - Trying cache after error...")
                cached_data = self.get_cached_data(users)
                if cached_data:
                    print("Debug - Using cached data after error")
                    return cached_data
            # Return None to indicate error
            print("Debug - No cache available or force refresh, returning None")
            return None

    def _enrich_prs_with_timeline(self, prs_by_user, force_refresh=False):
        """Helper method to enrich PRs with timeline data"""
        print(f"\nDebug - Enriching PRs with timeline data...")
        enriched = {}
        for user, prs in prs_by_user.items():
            print(f"Debug - Processing {len(prs)} PRs for user {user}")
            enriched[user] = []
            for pr in prs:
                try:
                    print(f"Debug - Fetching timeline for PR #{pr.number}")
                    timeline = self.get_pr_timeline(
                        pr.repo_owner, pr.repo_name, pr.number, force_refresh=force_refresh
                    )
                    print(f"Debug - Got {len(timeline) if timeline else 0} timeline events")
                    pr.timeline = timeline
                    enriched[user].append(pr)
                except Exception as e:
                    print(f"Warning: Error fetching timeline for PR #{pr.number}: {e}")
                    enriched[user].append(pr)  # Still add PR even if timeline fails
        return enriched

    def get_cached_data(self, users):
        """Get PR data from cache"""
        return get_cached_pr_data(self, users)

    def cache_data(self, users, data):
        """Cache PR data"""
        cache_pr_data(self, users, data)
