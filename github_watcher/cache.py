import os
import json
import xxhash
import shutil
from datetime import datetime, timedelta
from objects import TimelineEventType  # Import the enum


class Cache:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = cache_dir
        # Clean up cache directory on initialization
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
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
        elif hasattr(value, 'to_dict'):  # Handle objects with to_dict method
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
            with open(cache_file, 'r') as f:
                data = json.load(f)
                if datetime.fromisoformat(data['expiry']) < datetime.now():
                    os.remove(cache_file)
                    return None
                return self._deserialize_value(data['value'])
        except (json.JSONDecodeError, KeyError, ValueError):
            if os.path.exists(cache_file):
                os.remove(cache_file)
            return None
    
    def set(self, key, value, bucket="default", ttl=None):
        cache_file = self._get_cache_file(key, bucket)
        
        if ttl is None:
            ttl = timedelta(hours=1)  # Default TTL
        
        data = {
            'value': self._serialize_value(value),
            'expiry': (datetime.now() + ttl).isoformat()
        }
        
        with open(cache_file, 'w') as f:
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
