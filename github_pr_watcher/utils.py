import time
from datetime import datetime
from functools import wraps
from typing import List, ParamSpec, TypeVar, Callable

import requests

P = ParamSpec('P')
T = TypeVar('T')


def hex_to_rgba(bg_color, opacity):
    if bg_color.startswith("#"):
        r = int(bg_color[1:3], 16)
        g = int(bg_color[3:5], 16)
        b = int(bg_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, {opacity})"
    return bg_color


def parse_datetime(time_str: str) -> datetime | None:
    if time_str is None:
        return None
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def print_time(time_obj):
    return time_obj.strftime("%d-%m-%Y %H:%M:%S")


def flatten(list_of_lists: List[List[T]]) -> List[T]:
    return [item for sublist in list_of_lists for item in sublist]


def with_rate_limit_retry(
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to handle GitHub API rate limiting with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_multiplier: Multiplier for exponential backoff
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retries = 0
            backoff = initial_backoff

            while True:
                try:
                    response = func(*args, **kwargs)

                    # Check if we got a response object (not all functions return one)
                    if isinstance(response, requests.Response):
                        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

                        # If rate limited, wait and retry
                        if response.status_code == 403 and remaining == 0:
                            wait_time = max(0.0, reset_time - time.time())
                            if wait_time > 0:
                                print(f"Rate limited. Waiting {wait_time:.1f} seconds...")
                                time.sleep(wait_time)
                                continue

                        response.raise_for_status()
                    return response

                except requests.exceptions.RequestException as e:
                    if retries >= max_retries:
                        print(f"Max retries ({max_retries}) exceeded. Last error: {e}")
                        raise

                    # Calculate backoff time
                    wait_time = min(backoff, max_backoff)
                    print(f"Request failed: {e}. Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)

                    retries += 1
                    backoff *= backoff_multiplier

        return wrapper

    return decorator
