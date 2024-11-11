from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QSizePolicy, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import webbrowser

def create_badge(text, bg_color, fg_color="white", parent=None, min_width=45, opacity=1.0):
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

def create_changes_badge(additions, deletions, settings):
    """Create a badge showing additions and deletions with color gradient"""
    total_changes = additions + deletions
    bg_color = get_changes_color(total_changes, settings)

    changes_badge = QFrame()
    changes_badge.setStyleSheet(
        f"""
        QFrame {{
            background: {bg_color};
            border-radius: 10px;
            min-width: 100px;
            max-width: 120px;
            min-height: 20px;
            max-height: 20px;
            padding: 0px 6px;
        }}
        QLabel {{
            background: transparent;
            color: white;
            font-size: 10px;
            padding: 0px;
        }}
    """
    )

    layout = QHBoxLayout(changes_badge)
    layout.setContentsMargins(6, 0, 6, 0)
    layout.setSpacing(4)

    additions_label = QLabel(f"+{additions}")
    additions_label.setStyleSheet(
        "color: rgba(152, 255, 152, 0.9); font-size: 10px; font-weight: bold;"
    )
    layout.addWidget(additions_label)

    separator = QLabel("/")
    separator.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px;")
    layout.addWidget(separator)

    deletions_label = QLabel(f"-{deletions}")
    deletions_label.setStyleSheet(
        "color: rgba(255, 179, 179, 0.9); font-size: 10px; font-weight: bold;"
    )
    layout.addWidget(deletions_label)

    return changes_badge

def get_changes_color(total_changes, settings):
    """Calculate gradient color based on number of changes"""
    warning_level = settings.get("thresholds", {}).get("lines", {}).get("warning", 500)
    danger_level = settings.get("thresholds", {}).get("lines", {}).get("danger", 1000)

    if total_changes <= warning_level:
        return "rgba(40, 167, 69, 0.5)"  # Green with 0.5 opacity
    elif total_changes <= danger_level:
        ratio = (total_changes - warning_level) / (danger_level - warning_level)
        if ratio <= 0.5:
            return (
                f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 rgba(40, 167, 69, 0.5), "
                f"stop:1 rgba(255, 193, 7, 0.5))"
            )
        else:
            return (
                f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                f"stop:0 rgba(255, 193, 7, 0.5), "
                f"stop:1 rgba(220, 53, 69, 0.5))"
            )
    else:
        return "rgba(220, 53, 69, 0.5)"  # Red with 0.5 opacity

def create_pr_card(pr_data, settings, parent=None):
    """Create a card widget for a pull request"""
    print(f"\nDebug - Creating PR card for #{pr_data.number}:")
    print(f"  Title: {pr_data.title}")
    print(f"  State: {pr_data.state}")
    print(f"  Draft: {getattr(pr_data, 'draft', None)}")
    print(f"  Timeline events: {len(getattr(pr_data, 'timeline', []) or [])}")

    card = QFrame(parent)
    card.setObjectName("prCard")
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card.setStyleSheet(
        """
        QFrame#prCard {
            background-color: #2d2d2d;
            border-radius: 12px;
            padding: 10px;
            margin: 3px 0;
        }
        QFrame {
            background: transparent;
            border-radius: 12px;
        }
        QLabel {
            background: transparent;
        }
    """
    )

    layout = QVBoxLayout(card)
    layout.setSpacing(4)
    layout.setContentsMargins(10, 8, 10, 8)

    # Header section
    header = QVBoxLayout()
    header.setSpacing(4)

    # Top row with title and repo info
    top_row = QHBoxLayout()
    top_row.setSpacing(8)

    # Title with PR number
    title_text = f"{pr_data.title} (#{pr_data.number})"
    title = QLabel(title_text)
    title.setFont(QFont("", 13, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff; text-decoration: underline;")
    title.setCursor(Qt.CursorShape.PointingHandCursor)
    title.setWordWrap(True)

    if url := getattr(pr_data, "html_url", None):
        def open_url(event):
            webbrowser.open(url)
        title.mousePressEvent = open_url

    top_row.addWidget(title)

    # Add repo info
    repo_text = f"{pr_data.repo_owner}/{pr_data.repo_name}"
    repo_label = QLabel(repo_text)
    repo_label.setStyleSheet("color: #8b949e; font-size: 11px;")
    repo_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    top_row.addWidget(repo_label)

    header.addLayout(top_row)

    # Add badges
    badges_layout = QHBoxLayout()
    badges_layout.setSpacing(4)

    # Files badge
    files_count = getattr(pr_data, "changed_files", 0) or 0
    if files_count > 0:
        files_warning = settings.get("thresholds", {}).get("files", {}).get("warning", 10)
        files_danger = settings.get("thresholds", {}).get("files", {}).get("danger", 50)

        if files_count >= files_danger:
            badge_color = "#dc3545"  # Red
        elif files_count >= files_warning:
            badge_color = "#ffc107"  # Yellow
        else:
            badge_color = "#28a745"  # Green

        files_badge = create_badge(
            f"{files_count} files", badge_color, opacity=0.5
        )
        badges_layout.addWidget(files_badge)

    # Changes badge
    additions = getattr(pr_data, "additions", 0) or 0
    deletions = getattr(pr_data, "deletions", 0) or 0
    if additions > 0 or deletions > 0:
        changes_badge = create_changes_badge(additions, deletions, settings)
        badges_layout.addWidget(changes_badge)

    # Draft badge
    if getattr(pr_data, "draft", False):
        draft_badge = create_badge("Draft", "#6c757d", opacity=0.5)
        badges_layout.addWidget(draft_badge)

    badges_layout.addStretch()
    header.addLayout(badges_layout)
    layout.addLayout(header)

    return card 