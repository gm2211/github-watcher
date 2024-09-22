import json
import os
import xxhash
from datetime import datetime, timedelta
from github_watcher.objects import PullRequest, User, TimelineEvent
from enum import Enum
from typing import Dict, Any, Optional


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (PullRequest, User, TimelineEvent)):
            return obj.to_dict()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class CacheBucket:
    def __init__(self, name: str, expiration: timedelta):
        self.name = name
        self.expiration = expiration
        self.last_updated = datetime.now()
        self.entries: Dict[str, Any] = {}

    def is_expired(self) -> bool:
        return datetime.now() - self.last_updated > self.expiration

    def get(self, key: str) -> Optional[Any]:
        return self.entries.get(key)

    def set(self, key: str, value: Any) -> None:
        self.entries[key] = value
        self.last_updated = datetime.now()


class Cache:
    def __init__(self, cache_dir: str, default_expiration: timedelta = timedelta(minutes=10)):
        self.cache_dir = cache_dir
        self.default_expiration = default_expiration
        self.buckets: Dict[str, CacheBucket] = {}
        os.makedirs(cache_dir, exist_ok=True)

    @staticmethod
    def _hash_key(key: str) -> str:
        return xxhash.xxh64(key.encode()).hexdigest()

    def _get_bucket(self, bucket_name: str) -> CacheBucket:
        if bucket_name not in self.buckets:
            self.buckets[bucket_name] = CacheBucket(bucket_name, self.default_expiration)
            self._load_bucket(bucket_name)
        return self.buckets[bucket_name]

    def _load_bucket(self, bucket_name: str) -> None:
        file_path = os.path.join(self.cache_dir, f"{bucket_name}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    self.buckets[bucket_name] = CacheBucket(
                        bucket_name,
                        timedelta(seconds=data['expiration_seconds'])
                    )
                    self.buckets[bucket_name].last_updated = datetime.fromisoformat(data['last_updated'])
                    self.buckets[bucket_name].entries = data['entries']
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error loading bucket {bucket_name}: {str(e)}")
                # If there's an error, we'll create a new bucket

    def _save_bucket(self, bucket_name: str) -> None:
        bucket = self.buckets[bucket_name]
        file_path = os.path.join(self.cache_dir, f"{bucket_name}.json")
        with open(file_path, 'w') as f:
            json.dump(
                {
                    'expiration_seconds': bucket.expiration.total_seconds(),
                    'last_updated': bucket.last_updated.isoformat(),
                    'entries': bucket.entries
                }, f, cls=CustomJSONEncoder
            )

    def get(self, key: str, bucket_name: str = "default") -> Optional[Any]:
        bucket = self._get_bucket(bucket_name)
        if bucket.is_expired():
            return None
        return bucket.get(key)

    def set(self, key: str, value: Any, bucket_name: str = "default") -> None:
        self.cleanup()
        bucket = self._get_bucket(bucket_name)
        bucket.set(key, value)
        self._save_bucket(bucket_name)

    def cleanup(self) -> None:
        current_time = datetime.now()
        for bucket_name, bucket in list(self.buckets.items()):
            expired_keys = [key for key, value in bucket.entries.items()
                            if isinstance(value, dict) and 'expiration' in value
                            and current_time > value['expiration']]

            for key in expired_keys:
                del bucket.entries[key]

            if not bucket.entries:
                del self.buckets[bucket_name]
                file_path = os.path.join(self.cache_dir, f"{bucket_name}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                self._save_bucket(bucket_name)
