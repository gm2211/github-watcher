from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel


def format_time_diff(dt_str: str) -> str:
    """Format a datetime string into a human-readable time difference"""
    try:
        if not dt_str:
            return ""

        # Parse the datetime string
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

        # Calculate time difference
        now = datetime.now(timezone.utc)
        diff = now - dt

        # Convert to total seconds
        total_seconds = int(diff.total_seconds())

        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"

    except Exception as e:
        print(f"Error formatting time difference: {e}")
        return ""


def create_badge(
    text, bg_color, fg_color="white", parent=None, min_width=45, opacity=1.0
):
    """Create a styled badge widget"""
    badge = QFrame(parent)

    # Convert hex color to rgba with specified opacity
    if bg_color.startswith("#"):
        r = int(bg_color[1:3], 16)
        g = int(bg_color[3:5], 16)
        b = int(bg_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, {opacity})"

    badge.setStyleSheet(
        f"""
        QFrame {{
            background-color: {bg_color};
            border-radius: 10px;
            min-width: {min_width}px;
            max-width: {min_width + 20}px;
            min-height: 20px;
            max-height: 20px;
            padding: 0px 6px;
        }}
        QLabel {{
            background: transparent;
            color: {fg_color};
            font-size: 10px;
            padding: 0px;
        }}
    """
    )

    layout = QHBoxLayout(badge)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    return badge
