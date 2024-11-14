import json
import webbrowser
from datetime import datetime, time, timedelta
from typing import Optional

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

from .themes import Colors, Styles
from ..objects import PullRequest
from ..utils import hex_to_rgba, print_time


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


def format_time(delta, suffix="") -> str:
    """Format a timedelta into a human readable string"""
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds} secs{suffix}"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} mins{suffix}"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hrs{suffix}"

    days = hours // 24
    return f"{days} days{suffix}"


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

    if pr.html_url:

        def open_url(_ignored):
            webbrowser.open(pr.html_url)

        title.mousePressEvent = open_url

    title_layout.addWidget(title)
    json_button = QPushButton("{ }")
    json_button.setStyleSheet(Styles.PR_CARD_JSON_BUTTON)
    json_button.setFixedSize(30, 20)
    json_button.setToolTip("Show PR Data")

    # Add repo info and author
    info_container = QWidget()
    info_layout = QVBoxLayout(info_container)
    info_layout.setContentsMargins(0, 0, 0, 0)
    info_layout.setSpacing(2)

    # Repository info
    approved_by_text = (
        f" | approved by: {', '.join(pr.approved_by)}" if pr.approved_by else ""
    )
    info_text = f"{pr.repo_owner}/{pr.repo_name} | author: {pr.user.login if pr.user else 'N/A'}{approved_by_text}"
    info_label = QLabel(info_text)
    info_label.setStyleSheet(Styles.PR_CARD_LABELS)
    info_layout.addWidget(info_label)

    info_layout.addStretch()
    title_layout.addWidget(info_container)

    top_row.addWidget(title_container, stretch=0)
    top_row.addWidget(json_button)

    # Right side container for JSON button
    right_container = QWidget()
    right_layout = QVBoxLayout(right_container)
    right_layout.setContentsMargins(0, 2, 0, 2)
    right_layout.setSpacing(8)

    top_row.addWidget(right_container)

    header.addLayout(top_row)

    # Status badge (MERGED/CLOSED/OPEN)
    status_color = Colors.GREEN
    status_text = "OPEN"
    tooltip = f"Opened at: {pr.created_at}"

    if pr.merged or pr.merged_at:
        status_color = Colors.PURPLE  # Purple for merged
        status_text = "MERGED"
        tooltip = (
            f"Merged at: {print_time(pr.merged_at)}\n"
            f"Time since merge: {format_time(datetime.now().astimezone() - pr.merged_at)}"
        )
    elif pr.closed_at:
        status_color = Colors.RED
        status_text = "CLOSED"
        tooltip = f"Closed at: {pr.closed_at}"

    status_badge = create_badge(status_text, status_color, opacity=0.5)
    status_badge.setToolTip(tooltip)
    right_layout.addWidget(status_badge)

    # Draft badge
    if pr.draft:
        draft_badge = create_badge("DRAFT", "#6c757d", opacity=0.5)
        right_layout.addWidget(draft_badge)

    # Approval status badge
    if pr.approved_by:
        approval_badge = create_badge("APPROVED", Colors.SUCCESS_BG, opacity=0.5)
        first_approver = pr.approved_by[0]
        approval_badge.setToolTip(f"Approved by {first_approver}")

        right_layout.addWidget(approval_badge)
    elif pr.latest_reviews:
        # Show changes requested badge if any reviewer requested changes
        if any(
            state.lower() == "changes_requested" for state in pr.latest_reviews.values()
        ):
            changes_badge = create_badge("CHANGES REQUESTED", "#dc3545", opacity=0.5)
            right_layout.addWidget(changes_badge)

    # Bottom row
    bottom_layout = QHBoxLayout()
    bottom_layout.setSpacing(4)

    def show_json():
        dialog = JsonViewDialog(pr.to_dict(), parent)
        dialog.exec()

    json_button.clicked.connect(show_json)
    files_count = pr.changed_files or 0
    if files_count > 0:
        files_badge_color = compute_color(
            files_count,
            settings.thresholds.files.warning,
            settings.thresholds.files.danger,
        )
        files_badge = create_badge(
            f"{files_count} files", files_badge_color, opacity=0.5
        )
        bottom_layout.addWidget(files_badge)

    # Changes badge
    additions = pr.additions or 0
    deletions = pr.deletions or 0
    if additions > 0 or deletions > 0:
        changes_badge = create_changes_badge(additions, deletions, settings)
        bottom_layout.addWidget(changes_badge)

    # Comment count badge
    comment_count_badge = create_badge(
        f"{sum(pr.comment_count_by_author.values())} comments", "#007bff", opacity=0.5
    )
    comments_by_author_str = "\n".join(
        "{}: {}".format(author, comment_count)
        for author, comment_count in pr.comment_count_by_author.items()
    )
    comment_count_badge.setToolTip(f"Comments by author:\n" f"{comments_by_author_str}")
    bottom_layout.addWidget(comment_count_badge)

    # Age badge
    pr_age = datetime.now().astimezone() - pr.created_at
    age_badge_color = compute_color(
        pr_age.days,
        settings.thresholds.age.warning.to_days(),
        settings.thresholds.age.danger.to_days(),
    )

    age_badge = create_badge(
        f"{format_time(pr_age, ' old')}", age_badge_color, opacity=0.5
    )
    age_badge.setToolTip(f"Created at: {print_time(pr.created_at)}")
    bottom_layout.addWidget(age_badge)

    # Add merge duration badge if PR is merged
    if pr.merged_at:
        merge_duration = pr.merged_at - pr.created_at

        # Determine color based on thresholds
        merge_duration_badge_color = compute_color(
            merge_duration.days,
            settings.thresholds.time_to_merge.warning.to_days(),
            settings.thresholds.time_to_merge.danger.to_days(),
        )

        merge_duration_badge = create_badge(
            f"TTM: {format_time(merge_duration)}",
            merge_duration_badge_color,
            opacity=0.5,
        )
        merge_duration_badge.setToolTip(
            f"Time it took to merge: {format_time(merge_duration)}"
        )
        bottom_layout.addWidget(merge_duration_badge)

    if pr.last_comment_time:
        time_since_last_comment = datetime.now().astimezone() - pr.last_comment_time

        # Determine color based on thresholds
        tslc_badge_color = compute_color(
            time_since_last_comment.days,
            settings.thresholds.time_since_comment.warning.to_days(),
            settings.thresholds.time_since_comment.danger.to_days(),
        )

        time_since_last_comment_badge = create_badge(
            f"TSLC: {format_time(time_since_last_comment)}", 
            tslc_badge_color, 
            opacity=0.5
        )
        time_since_last_comment_badge.setToolTip(
            f"Time Since Last Comment: {format_time(time_since_last_comment)}\n"
            f"Last Comment at: {print_time(pr.last_comment_time)}\n"
            f"Last Comment by: {pr.last_comment_author}"
        )
        bottom_layout.addWidget(time_since_last_comment_badge)

    bottom_layout.addStretch()
    header.addLayout(bottom_layout)
    layout.addLayout(header)

    return card


def compute_color(value, warning_threshold, danger_threshold):
    if value >= warning_threshold:
        return Colors.RED
    elif value >= danger_threshold:
        return Colors.YELLOW
    else:
        return Colors.GREEN
