import json
import os
import xxhash
from datetime import datetime, timedelta
from github_watcher.objects import PullRequest, User, TimelineEvent
from enum import Enum


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (PullRequest, User, TimelineEvent)):
            return obj.to_dict()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class Cache:
    def __init__(self, cache_dir, cache_expiration=timedelta(minutes=10)):
        self.cache_dir = cache_dir
        self.cache_expiration = cache_expiration
        os.makedirs(cache_dir, exist_ok=True)

    def _hash_key(self, key):
        return xxhash.xxh64(key.encode()).hexdigest()

    def get(self, key):
        hashed_key = self._hash_key(key)
        file_path = os.path.join(self.cache_dir, f"{hashed_key}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    time_since_write_to_cache = datetime.now() - datetime.fromisoformat(data['cache_write_at'])
                    if time_since_write_to_cache < self.cache_expiration:
                        return data['value']
            except json.JSONDecodeError:
                # If there's a JSON decoding error, remove the corrupted cache file
                os.remove(file_path)
                print(f"Removed corrupted cache file: {file_path}")
            except Exception as e:
                print(f"Error reading cache file {file_path}: {str(e)}")
        return None

    def set(self, key, value):
        self.cleanup_expired_files()
        hashed_key = self._hash_key(key)
        file_path = os.path.join(self.cache_dir, f"{hashed_key}.json")
        with open(file_path, 'w') as f:
            json.dump(
                {
                    'cache_write_at': datetime.now().isoformat(),
                    'query': key,
                    'value': value
                }, f, cls=CustomJSONEncoder
            )

    def cleanup_expired_files(self):
        current_time = datetime.now()
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path) and filename.endswith('.json'):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        file_timestamp = datetime.fromisoformat(data['cache_write_at'])
                        if current_time - file_timestamp > self.cache_expiration:
                            os.remove(file_path)
                except (json.JSONDecodeError, KeyError, ValueError):
                    # If there's an error reading the file, remove it
                    os.remove(file_path)
                    print(f"Removed invalid cache file: {file_path}")
                except Exception as e:
                    print(f"Error processing cache file {file_path}: {str(e)}")
