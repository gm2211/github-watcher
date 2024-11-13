import json
import webbrowser
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .theme import Styles
from ..objects import PullRequest
from ..utils import hex_to_rgba
import traceback


class JsonViewDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PR Data")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Create text edit with JSON content
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(Styles.PR_CARD_JSON_DIALOG)

        # Format JSON with indentation
        json_str = json.dumps(data, indent=2, default=str)
        text_edit.setText(json_str)

        layout.addWidget(text_edit)


def create_badge(text, bg_color, parent=None, opacity=1.0):
    """Create a styled badge widget"""
    badge = QFrame(parent)

    # Convert hex color to rgba with specified opacity
    bg_color = hex_to_rgba(bg_color, opacity)

    badge.setStyleSheet(Styles.pr_card_badge(bg_color))

    layout = QHBoxLayout(badge)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    return badge


def create_changes_badge(additions, deletions, settings):
    """Create a badge showing additions and deletions with color gradient"""
    if additions <= settings.thresholds.additions.warning:
        left_color = "rgba(40, 167, 69, 0.5)"  # Green
    elif additions <= settings.thresholds.additions.danger:
        left_color = "rgba(255, 193, 7, 0.5)"  # Yellow
    else:
        left_color = "rgba(220, 53, 69, 0.5)"  # Red

    # Determine right color (deletions)
    if deletions <= settings.thresholds.deletions.warning:
        right_color = "rgba(40, 167, 69, 0.5)"  # Green
    elif deletions <= settings.thresholds.deletions.danger:
        right_color = "rgba(255, 193, 7, 0.5)"  # Yellow
    else:
        right_color = "rgba(220, 53, 69, 0.5)"  # Red

    bg_color = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {left_color}, stop:1 {right_color})"

    changes_badge = QFrame()
    changes_badge.setStyleSheet(Styles.pr_card_changes_badge(bg_color))

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


def format_time_ago(delta) -> str:
    """Format a timedelta into a human readable string"""
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} seconds old"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} minutes old"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours old"
    
    days = hours // 24
    return f"{days} days old"


def calculate_pr_age_days(pr: PullRequest) -> tuple[int, str]:
    """Calculate PR age in days and return formatted string"""
    if not pr.created_at:
        return 0, "0 seconds old"
        
    if isinstance(pr.created_at, str):
        # Handle both +00:00 and Z format
        created_at = datetime.fromisoformat(pr.created_at.replace('Z', '+00:00'))
    else:
        created_at = pr.created_at
    
    # Ensure both datetimes are timezone-aware
    now = datetime.now().astimezone()
    if created_at.tzinfo is None:
        created_at = created_at.astimezone()
    
    delta = now - created_at
    days = delta.days
    
    return days, format_time_ago(delta)


def create_pr_card(pr: PullRequest, settings, parent=None) -> QFrame:
    """Create a card widget for a pull request"""
    # Simplified debug logging - only show essential info
    print(f"Creating PR card for {pr.repo_owner}/{pr.repo_name}#{pr.number}")

    card = QFrame(parent)
    card.setObjectName("prCard")
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card.setStyleSheet(Styles.PR_CARD)

    layout = QVBoxLayout(card)
    layout.setSpacing(4)
    layout.setContentsMargins(10, 8, 10, 8)

    # Header section
    header = QVBoxLayout()
    header.setSpacing(4)

    # Top row with title, repo info, status badge and JSON button
    top_row = QHBoxLayout()
    top_row.setSpacing(8)

    # Title container to ensure proper width
    title_container = QWidget()
    title_container.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
    )
    title_layout = QVBoxLayout(title_container)
    title_layout.setContentsMargins(0, 0, 0, 0)
    title_layout.setSpacing(2)

    # Title with PR number
    title_text = f"{pr.title} (#{pr.number})"
    title = QLabel(title_text)
    title.setFont(QFont("", 13, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff; text-decoration: underline;")
    title.setCursor(Qt.CursorShape.PointingHandCursor)
    title.setWordWrap(True)
    title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    if url := getattr(pr, "html_url", None):

        def open_url(_ignored):
            webbrowser.open(url)

        title.mousePressEvent = open_url

    title_layout.addWidget(title)

    # Add repo info and author
    info_container = QWidget()
    info_layout = QHBoxLayout(info_container)
    info_layout.setContentsMargins(0, 0, 0, 0)
    info_layout.setSpacing(8)

    # Repository info
    repo_text = f"{pr.repo_owner}/{pr.repo_name}"
    repo_label = QLabel(repo_text)
    repo_label.setStyleSheet("color: #8b949e; font-size: 11px;")
    info_layout.addWidget(repo_label)

    # Separator
    separator = QLabel("•")
    separator.setStyleSheet("color: #8b949e; font-size: 11px;")
    info_layout.addWidget(separator)

    # Author info
    if hasattr(pr, "user") and pr.user:
        author_label = QLabel(f"author: {pr.user.login}")
        author_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        info_layout.addWidget(author_label)

    info_layout.addStretch()
    title_layout.addWidget(info_container)

    top_row.addWidget(title_container, stretch=1)

    # Right side container for status badge and JSON button
    right_container = QWidget()
    right_layout = QVBoxLayout(right_container)
    right_layout.setContentsMargins(0, 2, 0, 2)  # Small vertical margins
    right_layout.setSpacing(8)  # Increased spacing between badge and button from 6 to 8

    # Status badge (OPEN/CLOSED/MERGED)
    status_color = "#28a745"  # Default green for open
    status_text = "OPEN"

    if getattr(pr, "merged_at", None):
        status_color = "#6f42c1"  # Purple for merged
        status_text = "MERGED"
    elif getattr(pr, "closed_at", None):
        status_color = "#dc3545"  # Red for closed
        status_text = "CLOSED"

    status_badge = QFrame(right_container)
    status_badge.setStyleSheet(
        f"""
        QFrame {{
            background-color: {status_color};
            border-radius: 10px;
            min-width: 55px;
            max-width: 55px;
            min-height: 20px;
            max-height: 20px;
            margin: 0;
            padding: 0;
            opacity: 0.5;
        }}
        QLabel {{
            color: white;
            font-weight: 700;
            font-size: 11px;
            background: transparent;
            padding: 0;
            margin: 0;
        }}
    """
    )

    status_layout = QHBoxLayout(status_badge)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(0)

    status_label = QLabel(status_text)
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignCenter)

    # Container for status badge to ensure center alignment
    status_container = QWidget()
    status_container_layout = QHBoxLayout(status_container)
    status_container_layout.setContentsMargins(0, 0, 0, 0)
    status_container_layout.addWidget(
        status_badge, alignment=Qt.AlignmentFlag.AlignCenter
    )
    right_layout.addWidget(status_container)

    # Add JSON button
    json_button = QPushButton("{ }")
    json_button.setStyleSheet(Styles.PR_CARD_JSON_BUTTON)
    json_button.setFixedSize(30, 20)  # Made slightly shorter to match status badge
    json_button.setToolTip("Show PR Data")

    def show_json():
        dialog = JsonViewDialog(pr.to_dict(), parent)
        dialog.exec()

    json_button.clicked.connect(show_json)

    # Container for JSON button to ensure center alignment
    json_container = QWidget()
    json_container_layout = QHBoxLayout(json_container)
    json_container_layout.setContentsMargins(0, 0, 0, 0)
    json_container_layout.addWidget(json_button, alignment=Qt.AlignmentFlag.AlignCenter)
    right_layout.addWidget(json_container)

    top_row.addWidget(right_container)
    header.addLayout(top_row)

    # Add badges
    badges_layout = QHBoxLayout()
    badges_layout.setSpacing(4)

    # Draft badge
    if getattr(pr, "draft", False):
        draft_badge = create_badge("DRAFT", "#6c757d", opacity=0.5)
        badges_layout.addWidget(draft_badge)

    # Approval status badge
    if hasattr(pr, "timeline") and pr.timeline:
        latest_review = None
        for event in reversed(pr.timeline):
            if event.eventType in ["approved", "changes_requested"]:
                latest_review = event.eventType
                break

        if latest_review == "approved":
            approval_badge = create_badge("APPROVED", "#28a745", opacity=0.5)
            badges_layout.addWidget(approval_badge)
        elif latest_review == "changes_requested":
            changes_badge = create_badge("CHANGES REQUESTED", "#dc3545", opacity=0.5)
            badges_layout.addWidget(changes_badge)

    # Files badge
    files_count = getattr(pr, "changed_files", 0) or 0
    if files_count > 0:
        files_warning = settings.thresholds.files.warning
        files_danger = settings.thresholds.files.danger

        if files_count >= files_danger:
            badge_color = "#dc3545"  # Red
        elif files_count >= files_warning:
            badge_color = "#ffc107"  # Yellow
        else:
            badge_color = "#28a745"  # Green

        files_badge = create_badge(f"{files_count} files", badge_color, opacity=0.5)
        badges_layout.addWidget(files_badge)

    # Changes badge
    additions = getattr(pr, "additions", 0) or 0
    deletions = getattr(pr, "deletions", 0) or 0
    if additions > 0 or deletions > 0:
        changes_badge = create_changes_badge(additions, deletions, settings)
        badges_layout.addWidget(changes_badge)

    # Age badge
    age_days, age_text = calculate_pr_age_days(pr)
    age_warning = settings.thresholds.age.warning
    age_danger = settings.thresholds.age.danger

    if age_days >= age_danger:
        badge_color = "#dc3545"  # Red
    elif age_days >= age_warning:
        badge_color = "#ffc107"  # Yellow
    else:
        badge_color = "#28a745"  # Green

    age_badge = create_badge(age_text, badge_color, opacity=0.5)
    badges_layout.addWidget(age_badge)

    badges_layout.addStretch()
    header.addLayout(badges_layout)
    layout.addLayout(header)

    return card
