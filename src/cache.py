import os
import json
import xxhash
from datetime import datetime, timedelta
from src.objects import TimelineEventType, PullRequest  # Import both classes


class Cache:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = cache_dir
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_cache_file(self, key, bucket):
        # Use xxhash for faster hashing
        hashed_key = xxhash.xxh64(key).hexdigest()
        return os.path.join(self.cache_dir, f"{bucket}_{hashed_key}.json")

    def _serialize_value(self, value):
        """Convert value to JSON-serializable format"""
        if isinstance(value, (datetime, timedelta)):
            return value.isoformat()
        elif isinstance(value, TimelineEventType):  # Handle TimelineEventType enum
            return value.value  # Store the enum value
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        elif hasattr(value, "to_dict"):  # Handle objects with to_dict method
            return self._serialize_value(value.to_dict())
        return value

    def _deserialize_value(self, value):
        """Convert value back from JSON format"""
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                # Check if this is a TimelineEventType value
                try:
                    return TimelineEventType(value)
                except ValueError:
                    return value
        elif isinstance(value, dict):
            return {k: self._deserialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._deserialize_value(item) for item in value]
        return value

    def get(self, key, bucket="default"):
        cache_file = self._get_cache_file(key, bucket)
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
                if datetime.fromisoformat(data["expiry"]) < datetime.now():
                    os.remove(cache_file)
                    return None
                return self._deserialize_value(data["value"])
        except (json.JSONDecodeError, KeyError, ValueError):
            if os.path.exists(cache_file):
                os.remove(cache_file)
            return None

    def set(self, key, value, bucket="default", ttl=None):
        cache_file = self._get_cache_file(key, bucket)

        if ttl is None:
            ttl = timedelta(hours=1)  # Default TTL

        data = {
            "value": self._serialize_value(value),
            "expiry": (datetime.now() + ttl).isoformat(),
        }

        with open(cache_file, "w") as f:
            json.dump(data, f)

    def invalidate(self, key, bucket="default"):
        """Invalidate a specific cache entry"""
        cache_file = self._get_cache_file(key, bucket)
        if os.path.exists(cache_file):
            os.remove(cache_file)

    def invalidate_bucket(self, bucket):
        """Invalidate all cache entries in a bucket"""
        for file in os.listdir(self.cache_dir):
            if file.startswith(f"{bucket}_"):
                os.remove(os.path.join(self.cache_dir, file))


def get_cached_pr_data(github_prs, users):
    """Try to get PR data from cache"""
    print("\nDebug - Attempting to load from cache...")

    # Try to get data from cache
    cache_key = f"all_pr_data_{'-'.join(sorted(users))}"
    print(f"Debug - Cache key: {cache_key}")

    cached_data = github_prs.cache.get(cache_key, "all_pr_data")
    if cached_data:
        print(
            f"Debug - Found cached data from {cached_data.get('timestamp', 'unknown time')}"
        )
        print(f"Debug - Raw cached data: {cached_data}")  # Add this debug line

        try:
            # Convert cached dictionaries back to PullRequest objects
            open_prs = {
                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                for user, prs in cached_data.get("open_prs", {}).items()
            }
            needs_review = {
                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                for user, prs in cached_data.get("needs_review", {}).items()
            }
            needs_attention = {
                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                for user, prs in cached_data.get("needs_attention", {}).items()
            }
            recently_closed = {
                user: [PullRequest.parse_pr(pr_dict) for pr_dict in prs]
                for user, prs in cached_data.get("recently_closed", {}).items()
            }

            print(f"Debug - Cached data contains:")
            print(f"  - Open PRs: {sum(len(prs) for prs in open_prs.values())}")
            print(f"  - Needs Review: {sum(len(prs) for prs in needs_review.values())}")
            print(
                f"  - Needs Attention: {sum(len(prs) for prs in needs_attention.values())}"
            )
            print(
                f"  - Recently Closed: {sum(len(prs) for prs in recently_closed.values())}"
            )

            return (open_prs, needs_review, needs_attention, recently_closed)
        except Exception as e:
            print(f"Error parsing cached data: {e}")
            return None

    print("Debug - No valid cache found")
    return None


def cache_pr_data(github_prs, users, data):
    """Cache the complete PR data set"""
    cache_key = f"all_pr_data_{'-'.join(sorted(users))}"
    print(f"Debug - Caching data with key: {cache_key}")

    cache_data = {
        "open_prs": data[0],
        "needs_review": data[1],
        "needs_attention": data[2],
        "recently_closed": data[3],
        "timestamp": datetime.now().isoformat(),
    }

    print(f"Debug - Caching data from {cache_data['timestamp']}")
    print(f"Debug - Data contains:")
    print(f"  - Open PRs: {len(data[0])}")
    print(f"  - Needs Review: {len(data[1])}")
    print(f"  - Recently Closed: {len(data[2])}")

    github_prs.cache.set(cache_key, cache_data, "all_pr_data")
    print("\nDebug - Cached complete PR data set")
