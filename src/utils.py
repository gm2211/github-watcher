from datetime import datetime
from typing import List, T


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
