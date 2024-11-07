from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QDialog,
    QLineEdit, QSpinBox, QFormLayout, QTextEdit, QGroupBox, QComboBox,
    QTabWidget, QDialogButtonBox, QPlainTextEdit, QMessageBox, QCheckBox,
    QListView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QTransform, QPixmap, QPainter, QColor, QFontMetrics
import webbrowser
from datetime import datetime, timezone, timedelta
import platform
import os
from notifications import notify
import yaml
import time
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from objects import TimelineEventType
import shutil


class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.title = title  # Store original title
        self.prs = {}
        self.spinner_label = None  # Initialize as None
        self.spinner_timer = None  # Initialize as None
        self.is_loading = False  # Track loading state
        self.scroll_area = None  # Initialize scroll area as None
        self.content_widget = None  # Initialize content widget as None
        self.content_layout = None  # Initialize content layout as None
        self.is_expanded = True
        
        self.setStyleSheet("""
            QFrame#sectionFrame {
                background-color: #1e1e1e;
                border-radius: 12px;
                margin: 5px;
            }
            QFrame {
                background: transparent;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        # Create UI elements
        self.create_header()
        self.create_scroll_area()

    def create_header(self):
        """Create header section"""
        header_container = QFrame()
        header_container.setFixedHeight(30)
        header_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)
        
        # Left side of header (title, toggle, and spinner)
        left_header = QWidget()
        left_header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.left_layout = QHBoxLayout(left_header)  # Store reference to left_layout
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(5)
        
        # Title label with count
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        self.left_layout.addWidget(self.title_label)
        
        # Count label
        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet("""
            QLabel {
                color: #8b949e;
                font-size: 12px;
                padding-left: 5px;
            }
        """)
        self.left_layout.addWidget(self.count_label)
        
        # Create spinner
        self.create_spinner()
        
        # Toggle button
        self.toggle_button = QPushButton("▼")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #ffffff;
                padding: 0px 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #cccccc;
            }
        """)
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.clicked.connect(self.toggle_content)
        self.left_layout.addWidget(self.toggle_button)
        self.left_layout.addStretch()
        
        header_layout.addWidget(left_header)
        self.main_layout.addWidget(header_container)

    def create_scroll_area(self):
        """Create or recreate scroll area and content widget"""
        try:
            # Clean up old widgets if they exist
            if hasattr(self, 'scroll_area'):
                try:
                    self.scroll_area.deleteLater()
                except:
                    pass
            if hasattr(self, 'content_widget'):
                try:
                    self.content_widget.deleteLater()
                except:
                    pass
            
            # Create new widgets
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
            """)
            
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(5)
            
            self.scroll_area.setWidget(self.content_widget)
            self.main_layout.addWidget(self.scroll_area)
            
        except Exception as e:
            print(f"Error creating scroll area: {e}")

    def toggle_content(self):
        """Toggle the visibility of the content"""
        if not self.scroll_area:
            return
            
        self.is_expanded = not self.is_expanded
        self.scroll_area.setVisible(self.is_expanded)
        self.toggle_button.setText("▼" if self.is_expanded else "▶")

    def layout(self):
        """Get the content layout"""
        return self.content_layout if self.content_layout else self.main_layout

    def create_spinner(self):
        """Create spinner label and timer"""
        try:
            # Clean up old spinner if it exists
            if self.spinner_label:
                try:
                    self.spinner_label.deleteLater()
                except:
                    pass
            if self.spinner_timer:
                try:
                    self.spinner_timer.stop()
                    self.spinner_timer.deleteLater()
                except:
                    pass
            
            # Create new spinner
            self.spinner_label = QLabel("⟳")
            self.spinner_label.setFixedWidth(20)
            self.spinner_label.setStyleSheet("""
                QLabel {
                    color: #0d6efd;
                    font-size: 14px;
                    padding: 0 5px;
                }
            """)
            self.spinner_label.hide()  # Hidden by default
            
            # Add to layout if we have one
            if hasattr(self, 'left_layout'):
                self.left_layout.addWidget(self.spinner_label)
            
            # Create new timer
            self.spinner_timer = QTimer(self)
            self.spinner_timer.timeout.connect(self.rotate_spinner)
            self.spinner_timer.setInterval(50)  # 50ms for smoother rotation
            self.spinner_rotation = 0
            
        except Exception as e:
            print(f"Warning: Error creating spinner: {e}")
            self.spinner_label = None
            self.spinner_timer = None

    def start_loading(self):
        """Start loading animation"""
        if self.is_loading:
            return
            
        self.is_loading = True
        
        try:
            # Recreate spinner if it was deleted
            if not self.spinner_label or not self.spinner_label.parent():  # Check parent instead of isValid
                self.create_spinner()
            
            if self.spinner_label and self.spinner_label.parent():
                self.spinner_label.show()
                if self.spinner_timer:
                    self.spinner_timer.start()
        except RuntimeError:
            # If the Qt object was deleted, recreate it
            self.create_spinner()
            if self.spinner_label:
                self.spinner_label.show()
                if self.spinner_timer:
                    self.spinner_timer.start()
        except Exception as e:
            print(f"Warning: Error starting loading animation: {e}")

    def stop_loading(self):
        """Stop loading animation"""
        self.is_loading = False
        try:
            if self.spinner_timer and self.spinner_timer.isActive():
                self.spinner_timer.stop()
            if self.spinner_label and self.spinner_label.parent():  # Check parent instead of isValid
                self.spinner_label.hide()
        except RuntimeError:
            # Qt object already deleted, just ignore
            pass
        except Exception as e:
            print(f"Warning: Error stopping loading animation: {e}")

    def rotate_spinner(self):
        """Rotate the spinner icon"""
        if not hasattr(self, 'spinner_rotation'):
            self.spinner_rotation = 0
        
        self.spinner_rotation = (self.spinner_rotation + 30) % 360
        self.spinner_label.setStyleSheet(f"""
            QLabel {{
                color: #0d6efd;
                font-size: 16px;
                padding: 0 5px;
                transform: rotate({self.spinner_rotation}deg);
            }}
        """)

    def update_count(self, count):
        """Update the count display"""
        self.count_label.setText(f"({count})")


def create_badge(text, bg_color, fg_color="white", parent=None, min_width=45, opacity=1.0):
    badge = QFrame(parent)
    
    # Convert hex color to rgba with specified opacity
    if bg_color.startswith('#'):
        r = int(bg_color[1:3], 16)
        g = int(bg_color[3:5], 16)
        b = int(bg_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, {opacity})"
    
    badge.setStyleSheet(f"""
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
    """)
    
    layout = QHBoxLayout(badge)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    return badge


def create_pr_card(pr_data, settings, parent=None):
    print(f"\nDebug - Creating PR card for #{pr_data.number}:")
    print(f"  Title: {pr_data.title}")
    print(f"  State: {pr_data.state}")
    print(f"  Draft: {getattr(pr_data, 'draft', None)}")
    print(f"  Timeline events: {len(getattr(pr_data, 'timeline', []) or [])}")
    
    if isinstance(pr_data, list):
        if not pr_data:
            label = QLabel("No PRs to display")
            return label
        pr_data = pr_data[0]
    
    card = QFrame(parent)
    card.setObjectName("prCard")
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card.setStyleSheet("""
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
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(4)  # Reduced overall spacing
    layout.setContentsMargins(10, 8, 10, 8)  # Slightly reduced margins
    
    # Header section with title and badges
    header = QVBoxLayout()
    header.setSpacing(4)
    
    # Top row with title and repo info
    top_row = QHBoxLayout()
    top_row.setSpacing(8)
    
    # Title with PR number
    title_text = f"{getattr(pr_data, 'title', 'Untitled')} (#{getattr(pr_data, 'number', '?')})"
    title = QLabel(title_text)
    title.setFont(QFont("", 13, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff; text-decoration: underline; background: transparent;")
    title.setCursor(Qt.CursorShape.PointingHandCursor)
    title.setWordWrap(True)
    
    # Create a proper event handler for the click
    if url := getattr(pr_data, 'html_url', None):
        def open_url(event):
            webbrowser.open(url)
        title.mousePressEvent = open_url
    
    top_row.addWidget(title)
    
    # Add repo info
    repo_text = f"{pr_data.repo_owner}/{pr_data.repo_name}"
    repo_label = QLabel(repo_text)
    repo_label.setStyleSheet("color: #8b949e; font-size: 11px; background: transparent;")
    repo_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    top_row.addWidget(repo_label)
    
    header.addLayout(top_row)
    
    # Badges row
    badges_layout = QHBoxLayout()
    badges_layout.setSpacing(4)
    
    # Left side badges (files and changes)
    left_badges = QHBoxLayout()
    left_badges.setSpacing(4)
    
    files_count = getattr(pr_data, 'changed_files', 0) or 0
    if files_count > 0:
        files_warning = settings.get('thresholds', {}).get('files', {}).get('warning', 10)
        files_danger = settings.get('thresholds', {}).get('files', {}).get('danger', 50)
        
        files_color = (
            "#28a745" if files_count < files_warning 
            else "#f0ad4e" if files_count < files_danger 
            else "#dc3545"
        )
        files_badge = create_badge(f"{files_count} files", files_color, min_width=60, opacity=0.7)
        left_badges.addWidget(files_badge)
    
    additions = getattr(pr_data, 'additions', 0) or 0
    deletions = getattr(pr_data, 'deletions', 0) or 0
    if additions > 0 or deletions > 0:
        total_changes = additions + deletions
        warning_level = settings.get('thresholds', {}).get('lines', {}).get('warning', 500)
        danger_level = settings.get('thresholds', {}).get('lines', {}).get('danger', 1000)
        
        changes_color = (
            "#28a745" if total_changes < warning_level
            else "#f0ad4e" if total_changes < danger_level
            else "#dc3545"
        )
        
        changes_badge = create_badge(
            f"+{additions} -{deletions}",
            changes_color,
            min_width=80,
            opacity=0.7
        )
        left_badges.addWidget(changes_badge)
    
    badges_layout.addLayout(left_badges)
    badges_layout.addStretch()  # Push status badges to the right
    
    # Right side badges
    right_badges = QHBoxLayout()
    right_badges.setSpacing(4)
    
    # Status badges (full opacity)
    if getattr(pr_data, 'draft', False):
        draft_badge = create_badge("DRAFT", "#6c757d", opacity=1.0)  # Gray
        right_badges.addWidget(draft_badge)
    
    # Check for review status in timeline
    if timeline := getattr(pr_data, 'timeline', []) or []:
        latest_review_state = None
        latest_review_author = None
        for event in reversed(timeline):  # Go through events from newest to oldest
            if event.eventType in [TimelineEventType.APPROVED, TimelineEventType.CHANGES_REQUESTED]:
                latest_review_state = event.eventType
                latest_review_author = event.author.login if event.author else None
                break
        
        if latest_review_state == TimelineEventType.APPROVED:
            approved_text = "APPROVED"
            if latest_review_author:
                approved_text += f" by {latest_review_author}"
            approved_badge = create_badge(approved_text, "#28a745", opacity=1.0)  # Green
            right_badges.addWidget(approved_badge)
        elif latest_review_state == TimelineEventType.CHANGES_REQUESTED:
            changes_text = "CHANGES REQUESTED"
            if latest_review_author:
                changes_text += f" by {latest_review_author}"
            changes_badge = create_badge(changes_text, "#dc3545", opacity=1.0)  # Red
            right_badges.addWidget(changes_badge)
    
    # Status badge colors
    MERGED_COLOR = "#6f42c1"  # Purple
    CLOSED_COLOR = "#dc3545"  # Red
    OPEN_COLOR = "#28a745"    # Green
    
    # Debug PR status
    merged_at = getattr(pr_data, 'merged_at', None)
    closed_at = getattr(pr_data, 'closed_at', None)
    state = str(getattr(pr_data, 'state', '')).lower()
    timeline = getattr(pr_data, 'timeline', []) or []
    
    # Check if PR is merged - for now assume closed PRs are merged
    # This is temporary until we fix the GitHub API query
    is_merged = (
        merged_at is not None or 
        any(getattr(event, 'eventType', None) == TimelineEventType.MERGED for event in timeline) or
        (closed_at is not None and state == 'closed')  # Assume closed means merged for now
    )
    
    print(f"\nDebug - PR #{pr_data.number} status:")
    print(f"  merged_at: {merged_at}")
    print(f"  closed_at: {closed_at}")
    print(f"  state: {state}")
    print(f"  is_merged: {is_merged}")
    
    # Status badge
    if is_merged:
        print(f"  -> Setting MERGED badge")
        status_badge = create_badge("MERGED", MERGED_COLOR, opacity=1.0)
    elif closed_at is not None:
        print(f"  -> Setting CLOSED badge")
        status_badge = create_badge("CLOSED", CLOSED_COLOR, opacity=1.0)
    else:
        print(f"  -> Setting OPEN badge")
        status_badge = create_badge("OPEN", OPEN_COLOR, opacity=1.0)
    right_badges.addWidget(status_badge)
    
    badges_layout.addLayout(right_badges)
    header.addLayout(badges_layout)
    layout.addLayout(header)
    
    # Add a small separator
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setStyleSheet("background-color: #404040; margin: 4px 0;")
    separator.setMaximumHeight(1)
    layout.addWidget(separator)
    
    # Info section
    info_container = QFrame()
    info_layout = QHBoxLayout(info_container)
    info_layout.setContentsMargins(0, 0, 0, 0)
    info_layout.setSpacing(4)  # Reduced spacing between elements
    
    # Left info
    left_info = QVBoxLayout()
    left_info.setSpacing(1)  # Reduced from 2 to 1 for tighter spacing
    
    # Author info
    user = getattr(pr_data, 'user', None)
    if user and hasattr(user, 'login'):
        author_text = f"Author: {user.login}"
        author_label = QLabel(author_text)
        author_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
        left_info.addWidget(author_label)
    
    # Comments info
    if timeline := getattr(pr_data, 'timeline', []):
        comments = [event for event in timeline if event.eventType == TimelineEventType.COMMENTED]
        comments_count = len(comments)
        if comments_count > 0:
            comments_text = f"💬 {comments_count} comment{'s' if comments_count != 1 else ''}"
            comments_label = QLabel(comments_text)
            comments_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
            left_info.addWidget(comments_label)
            
            # Show latest comment info
            latest_comment = comments[-1]
            if latest_comment and latest_comment.author:
                comment_author = latest_comment.author.login if hasattr(latest_comment.author, 'login') else latest_comment.author.name
                comment_date = latest_comment.created_at
                
                if comment_date:
                    now = datetime.now(timezone.utc)
                    time_diff = now - comment_date
                    time_text = format_time_diff(time_diff)
                    last_comment_text = f"Last comment by {comment_author} {time_text}"
                    last_comment_label = QLabel(last_comment_text)
                    last_comment_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
                    left_info.addWidget(last_comment_label)
    
    info_layout.addLayout(left_info)
    
    # Right info
    right_info = QVBoxLayout()
    right_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    
    if updated := getattr(pr_data, 'updated_at', None):
        try:
            if isinstance(updated, str):
                # Handle both ISO 8601 formats with timezone offset and Z
                if updated.endswith('Z'):
                    updated_date = datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                else:
                    updated_date = datetime.fromisoformat(updated)
            else:
                updated_date = updated
            
            now = datetime.now(timezone.utc)
            time_diff = now - updated_date
            time_text = f"Updated {format_time_diff(time_diff)}"
            
            updated_label = QLabel(time_text)
            updated_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            right_info.addWidget(updated_label)
        except (ValueError, TypeError) as e:
            print(f"Error parsing update date: {e} (value: {updated})")
    
    info_layout.addLayout(right_info)
    layout.addWidget(info_container)
    
    return card


def format_time_diff(time_diff):
    minutes = int(time_diff.total_seconds() / 60)
    hours = int(minutes / 60)
    days = int(hours / 24)
    
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{days} day{'s' if days != 1 else ''} ago"


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Users tab
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        
        # Users list
        users_group = QGroupBox("GitHub Users to Watch")
        users_group_layout = QVBoxLayout(users_group)
        
        self.users_text = QTextEdit()
        self.users_text.setPlaceholderText("Enter GitHub usernames, one per line")
        current_users = load_settings().get('users', [])
        self.users_text.setText("\n".join(current_users))
        users_group_layout.addWidget(self.users_text)
        
        users_layout.addWidget(users_group)
        tabs.addTab(users_tab, "Users")
        
        # Timing tab
        timing_tab = QWidget()
        timing_layout = QFormLayout(timing_tab)
        
        # Cache settings
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_value = QSpinBox()
        self.cache_value.setRange(1, 24)
        current_cache = load_settings().get('cache', {})
        self.cache_value.setValue(current_cache.get('value', 1))
        self.cache_unit = QComboBox()
        self.cache_unit.addItems(['hours'])
        self.cache_unit.setCurrentText(current_cache.get('unit', 'hours'))
        
        cache_row = QHBoxLayout()
        cache_row.addWidget(self.cache_value)
        cache_row.addWidget(self.cache_unit)
        
        cache_layout.addRow("Cache Duration:", cache_row)
        
        # Add Clear Cache button
        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.clicked.connect(self.clear_cache)
        cache_layout.addRow("", clear_cache_btn)
        
        timing_layout.addWidget(cache_group)
        
        # Refresh settings
        refresh_group = QGroupBox("Refresh Settings")
        refresh_layout = QFormLayout(refresh_group)
        
        self.refresh_value = QSpinBox()
        self.refresh_value.setRange(1, 60)
        current_refresh = load_settings().get('refresh', {})
        self.refresh_value.setValue(current_refresh.get('value', 30))
        self.refresh_unit = QComboBox()
        self.refresh_unit.addItems(['seconds', 'minutes', 'hours'])
        self.refresh_unit.setCurrentText(current_refresh.get('unit', 'seconds'))
        
        refresh_row = QHBoxLayout()
        refresh_row.addWidget(self.refresh_value)
        refresh_row.addWidget(self.refresh_unit)
        
        refresh_layout.addRow("Refresh Interval:", refresh_row)
        
        timing_layout.addWidget(refresh_group)
        tabs.addTab(timing_tab, "Timing")
        
        # Thresholds tab
        thresholds_tab = QWidget()
        thresholds_layout = QVBoxLayout(thresholds_tab)
        
        # Files thresholds
        files_group = QGroupBox("Files Changed Thresholds")
        files_layout = QFormLayout(files_group)
        
        current_thresholds = load_settings().get('thresholds', {})
        files_thresholds = current_thresholds.get('files', {})
        
        self.files_warning = QSpinBox()
        self.files_warning.setRange(1, 100)
        self.files_warning.setValue(files_thresholds.get('warning', 10))
        files_layout.addRow("Warning Level:", self.files_warning)
        
        self.files_danger = QSpinBox()
        self.files_danger.setRange(1, 1000)
        self.files_danger.setValue(files_thresholds.get('danger', 50))
        files_layout.addRow("Danger Level:", self.files_danger)
        
        thresholds_layout.addWidget(files_group)
        
        # Lines changed thresholds
        lines_group = QGroupBox("Lines Changed Thresholds")
        lines_layout = QFormLayout(lines_group)
        
        lines_thresholds = current_thresholds.get('lines', {})
        
        self.lines_warning = QSpinBox()
        self.lines_warning.setRange(1, 1000)
        self.lines_warning.setValue(lines_thresholds.get('warning', 500))
        lines_layout.addRow("Warning Level:", self.lines_warning)
        
        self.lines_danger = QSpinBox()
        self.lines_danger.setRange(1, 10000)
        self.lines_danger.setValue(lines_thresholds.get('danger', 1000))
        lines_layout.addRow("Danger Level:", self.lines_danger)
        
        thresholds_layout.addWidget(lines_group)
        
        # Recently Closed threshold
        recent_group = QGroupBox("Recently Closed Settings")
        recent_layout = QFormLayout(recent_group)
        
        self.recent_threshold = QSpinBox()
        self.recent_threshold.setRange(1, 30)
        self.recent_threshold.setValue(current_thresholds.get('recently_closed_days', 7))
        recent_layout.addRow("Show PRs closed within (days):", self.recent_threshold)
        
        thresholds_layout.addWidget(recent_group)
        
        # Add some stretch at the bottom
        thresholds_layout.addStretch()
        
        tabs.addTab(thresholds_tab, "Thresholds")
        
        layout.addWidget(tabs)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_settings(self):
        """Get current settings from dialog"""
        settings = load_settings()  # Get existing settings as base
        
        # Update users
        users_text = self.users_text.toPlainText()
        settings['users'] = [u.strip() for u in users_text.split('\n') if u.strip()]
        
        # Update cache settings
        settings['cache'] = {
            'value': self.cache_value.value(),
            'unit': self.cache_unit.currentText()
        }
        
        # Update refresh settings
        settings['refresh'] = {
            'value': self.refresh_value.value(),
            'unit': self.refresh_unit.currentText()
        }
        
        # Update thresholds
        settings['thresholds'] = {
            'files': {
                'warning': self.files_warning.value(),
                'danger': self.files_danger.value()
            },
            'lines': {
                'warning': self.lines_warning.value(),
                'danger': self.lines_danger.value()
            },
            'recently_closed_days': self.recent_threshold.value()
        }
        
        return settings

    def clear_cache(self):
        """Clear the cache directory"""
        try:
            cache_dir = ".cache"
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)  # Recreate empty cache dir
                QMessageBox.information(self, "Success", "Cache cleared successfully!")
            else:
                QMessageBox.information(self, "Info", "Cache directory does not exist.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear cache: {str(e)}")

    def test_notification(self):
        """Send a test notification"""
        notify(
            "Test Notification",
            "This is a test notification from GitHub PR Watcher"
        )


class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)  # Start hidden
        
        # Initialize timer first
        self.timer = None
        self.rotation = 0
        
        # Semi-transparent dark background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 12px;
                background: transparent;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Loading text
        loading_label = QLabel("Refreshing...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading_label)
        
        # Spinner emoji that rotates
        self.spinner_label = QLabel("⟳")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                background: transparent;
            }
        """)
        layout.addWidget(self.spinner_label)
    
    def rotate_spinner(self):
        if hasattr(self, 'rotation'):  # Safety check
            self.rotation = (self.rotation + 30) % 360
            self.spinner_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: 24px;
                    background: transparent;
                    qproperty-alignment: AlignCenter;
                    transform: rotate({self.rotation}deg);
                }}
            """)
    
    def showEvent(self, event):
        if not self.timer:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.rotate_spinner)
            self.timer.setInterval(100)  # Rotate every 100ms
        self.timer.start()
        super().showEvent(event)
    
    def hideEvent(self, event):
        if hasattr(self, 'timer') and self.timer:  # Double safety check
            self.timer.stop()
        super().hideEvent(event)


class RefreshWorker(QThread):
    finished = pyqtSignal(tuple)  # Signal to emit when refresh is complete
    error = pyqtSignal(str)       # Signal to emit when an error occurs
    progress = pyqtSignal(str)    # Signal to emit progress updates
    
    def __init__(self, github_prs, users, section=None):
        super().__init__()
        self.github_prs = github_prs
        self.users = users
        self.section = section
        
    def run(self):
        try:
            section_names = {
                'open': 'Open PRs',
                'review': 'Needs Review',
                'attention': 'Changes Requested',
                'closed': 'Recently Closed'
            }
            section_name = section_names.get(self.section, self.section)
            self.progress.emit(f"Loading {section_name}...")
            
            print(f"\nDebug - Worker: Fetching {self.section} PR data...")
            new_data = self.github_prs.get_pr_data(self.users, force_refresh=True, section=self.section)
            if new_data is not None:
                self.progress.emit(f"Completed {section_name}")
                self.finished.emit(new_data)
            else:
                self.error.emit(f"Refresh failed for section {self.section}, no data returned")
        except Exception as e:
            self.error.emit(str(e))


class MultiSelectComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setView(QListView())
        self.view().pressed.connect(self.handle_item_pressed)
        self.selected_items = set()
        
        # Style the view
        self.view().setStyleSheet("""
            QListView {
                background-color: #2d2d2d;
                border: 1px solid #404040;
            }
            QListView::item {
                padding: 3px;
            }
            QListView::item:selected {
                background-color: #0d6efd;
                color: white;
            }
            QListView::item:hover {
                background-color: #404040;
            }
        """)
    
    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if not item:
            return
            
        if index.row() == 0:  # "All Authors"
            self.selected_items.clear()
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
                # Uncheck all other items
                for i in range(1, self.count()):
                    self.model().item(i).setCheckState(Qt.CheckState.Unchecked)
        else:
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
                self.selected_items.discard(item.text())
                # If no items selected, check "All Authors"
                if not self.selected_items:
                    self.model().item(0).setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
                self.selected_items.add(item.text())
                # Uncheck "All Authors"
                self.model().item(0).setCheckState(Qt.CheckState.Unchecked)
        
        # Update display text
        self.updateText()
        
        # Emit current text changed signal
        self.currentTextChanged.emit(self.currentText())
    
    def updateText(self):
        if not self.selected_items:
            self.setCurrentText("All Authors")
        else:
            self.setCurrentText(", ".join(sorted(self.selected_items)))
    
    def addItem(self, text):
        super().addItem(text)
        item = self.model().item(self.count() - 1)
        item.setCheckState(Qt.CheckState.Unchecked)
        if text == "All Authors":
            item.setCheckState(Qt.CheckState.Checked)
    
    def getSelectedItems(self):
        return self.selected_items if self.selected_items else {"All Authors"}


class PRWatcherUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub PR Watcher")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create section frames first
        self.needs_review_frame = SectionFrame("Needs Review")
        self.changes_requested_frame = SectionFrame("Changes Requested")
        self.open_prs_frame = SectionFrame("Open PRs")
        self.recently_closed_frame = SectionFrame("Recently Closed")
        
        # Create header with buttons
        header_layout = QHBoxLayout()
        
        # Left side: loading indicator and title
        left_layout = QHBoxLayout()
        
        # Loading indicator (just text, no spinner)
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #0d6efd;
                font-size: 12px;
                padding: 0 5px;
            }
        """)
        self.loading_label.hide()  # Hidden by default
        left_layout.addWidget(self.loading_label)
        
        # Title
        title = QLabel("GitHub PR Watcher")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        left_layout.addWidget(title)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()  # Push buttons to the right
        
        # Buttons container
        buttons_layout = QHBoxLayout()
        
        # Test notification button
        test_notif_btn = QPushButton("🔔 Test")
        test_notif_btn.clicked.connect(self.show_test_notification)
        test_notif_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        test_notif_btn.setFixedWidth(80)  # Fixed width
        test_notif_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
                font-size: 12px;  /* Smaller font */
                height: 25px;     /* Fixed height */
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        buttons_layout.addWidget(test_notif_btn)
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        refresh_btn.setFixedWidth(80)  # Fixed width
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
                font-size: 12px;  /* Smaller font */
                height: 25px;     /* Fixed height */
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        buttons_layout.addWidget(refresh_btn)
        
        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        settings_btn.setFixedWidth(30)  # Square button
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 5px;
                padding: 5px;
                color: white;
                font-size: 14px;
                height: 25px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        buttons_layout.addWidget(settings_btn)
        
        header_layout.addLayout(buttons_layout)
        main_layout.addLayout(header_layout)
        
        # Add filters container
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        
        # Draft toggle
        self.show_drafts_toggle = QCheckBox("Show Draft PRs")
        self.show_drafts_toggle.setChecked(True)
        self.show_drafts_toggle.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 12px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #404040;
                background: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background: #0d6efd;
            }
            QCheckBox::indicator:hover {
                border-color: #505050;
            }
        """)
        self.show_drafts_toggle.stateChanged.connect(self.toggle_drafts_visibility)
        filters_layout.addWidget(self.show_drafts_toggle)
        
        # Group by user toggle
        self.group_by_user_toggle = QCheckBox("Group by User")
        self.group_by_user_toggle.setChecked(False)
        self.group_by_user_toggle.setStyleSheet(self.show_drafts_toggle.styleSheet())
        self.group_by_user_toggle.stateChanged.connect(self.toggle_user_grouping)
        filters_layout.addWidget(self.group_by_user_toggle)
        
        # User filter
        user_filter_container = QWidget()
        user_filter_layout = QHBoxLayout(user_filter_container)
        user_filter_layout.setContentsMargins(0, 0, 0, 0)
        user_filter_layout.setSpacing(5)
        
        # User filter label
        user_filter_label = QLabel("Filter by Author:")
        user_filter_label.setStyleSheet("color: white; font-size: 12px;")
        user_filter_layout.addWidget(user_filter_label)
        
        # User filter combobox
        self.user_filter = MultiSelectComboBox()
        self.user_filter.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 3px;
                color: white;
                padding: 3px 10px;
                min-width: 200px;  /* Increased width for multiple selections */
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down-arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        self.user_filter.currentTextChanged.connect(self.apply_filters)
        user_filter_layout.addWidget(self.user_filter)
        
        filters_layout.addWidget(user_filter_container)
        filters_layout.addStretch()  # Push filters to the left
        
        left_layout.addLayout(filters_layout)
        
        # Initialize user filter with "All Authors"
        self.user_filter.addItem("All Authors")
        
        # Create scroll area for sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Add sections to scroll area
        scroll_layout.addWidget(self.needs_review_frame)
        scroll_layout.addWidget(self.changes_requested_frame)
        scroll_layout.addWidget(self.open_prs_frame)
        scroll_layout.addWidget(self.recently_closed_frame)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Initialize auto refresh timer
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        
        # Initialize tracking for PRs with empty sets
        self.previously_open_prs = set()
        self.previously_closed_prs = set()
        self.notified_prs = set()
        self.initial_state = True
        
        # Set window size and style
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        # Initialize worker list
        self.workers = []
        
        # Initialize worker to None
        self.refresh_worker = None
        self.consecutive_failures = 0
        self.max_backoff = 5
        
        # Add progress label next to spinner
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #0d6efd;
                font-size: 12px;
                padding: 0 5px;
            }
        """)
        self.progress_label.hide()
        left_layout.addWidget(self.progress_label)
        
        # Initialize sections dict to track loading state
        self.loading_sections = {}
    
    def show_test_notification(self):
        notify("GitHub PR Watcher", "Test notification - System is working!")

    def refresh_data(self):
        if self.refresh_worker and self.refresh_worker.isRunning():
            print("Debug - Refresh already in progress, skipping")
            return
            
        print("\nDebug - Starting refresh...")
        self.loading_label.show()
        
        # Create and start worker thread
        self.refresh_worker = RefreshWorker(self.github_prs, self.settings.get('users', []))
        self.refresh_worker.finished.connect(lambda data: self.handle_refresh_success(data))  # Use lambda to handle data
        self.refresh_worker.error.connect(self.handle_refresh_error)
        self.refresh_worker.finished.connect(lambda _: self.cleanup_worker(self.refresh_worker))  # Pass worker explicitly
        self.refresh_worker.error.connect(lambda _: self.cleanup_worker(self.refresh_worker))  # Pass worker explicitly
        self.refresh_worker.start()

    def handle_refresh_success(self, new_data):
        print("Debug - Refresh completed successfully")
        self.update_pr_lists(*new_data)
        self.consecutive_failures = 0
        self.loading_label.hide()

    def handle_refresh_error(self, error_msg):
        print(f"Error refreshing data: {error_msg}")
        self.consecutive_failures += 1
        print(f"Consecutive failures: {self.consecutive_failures}")
        self.loading_label.hide()

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop refresh timer
            if hasattr(self, 'auto_refresh_timer'):
                self.auto_refresh_timer.stop()
            
            # Force quit any running workers
            if hasattr(self, 'refresh_worker') and self.refresh_worker:
                self.refresh_worker.terminate()  # Force terminate if running
                self.refresh_worker.wait(1000)   # Wait max 1 second
            
            # Clean up other workers
            if hasattr(self, 'workers'):
                for worker in self.workers[:]:
                    worker.terminate()  # Force terminate
                    worker.wait(1000)   # Wait max 1 second
                self.workers.clear()
            
            print("Debug - Application cleanup completed")
            event.accept()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
            event.accept()  # Accept the close event anyway

    def set_refresh_callback(self, callback):
        self.refresh_callback = callback

    def update_pr_lists(self, open_prs_by_user, prs_awaiting_review_by_user,
                        prs_that_need_attention_by_user, user_recently_closed_prs_by_user):
        # Get current state
        current_open_prs = set()
        current_closed_prs = set()
        pr_objects = {}  # Store PR objects by number for easy lookup
        
        # Process open PRs
        if isinstance(open_prs_by_user, dict):
            for prs in open_prs_by_user.values():
                for pr in prs:
                    pr_num = getattr(pr, 'number', None)
                    if pr_num:
                        current_open_prs.add(pr_num)
                        pr_objects[pr_num] = pr
        
        # Process closed PRs
        if isinstance(user_recently_closed_prs_by_user, dict):
            for prs in user_recently_closed_prs_by_user.values():
                for pr in prs:
                    pr_num = getattr(pr, 'number', None)
                    if pr_num:
                        current_closed_prs.add(pr_num)
                        pr_objects[pr_num] = pr
                        # Remove from open PRs if it was just closed
                        if pr_num in current_open_prs:
                            current_open_prs.remove(pr_num)
                            if isinstance(open_prs_by_user, dict):
                                for user_prs in open_prs_by_user.values():
                                    user_prs[:] = [p for p in user_prs if p.number != pr_num]
        
        if not hasattr(self, 'initial_state'):
            self.initial_state = True
            self.previously_open_prs = set()
            self.previously_closed_prs = set()
        
        if self.initial_state:
            # Initialize state without notifications
            self.previously_open_prs = current_open_prs.copy()
            self.previously_closed_prs = current_closed_prs.copy()
            self.initial_state = False
            print("\nDebug - Initialized PR state without notifications")
        else:
            # Find state changes
            disappeared_from_open = self.previously_open_prs - current_open_prs
            newly_closed = disappeared_from_open & current_closed_prs
            
            # A PR is new only if it wasn't previously open AND wasn't previously closed
            new_prs = current_open_prs - self.previously_open_prs - self.previously_closed_prs
            
            # A PR is reopened if it was previously closed and is now open
            reopened_prs = current_open_prs & self.previously_closed_prs
            
            print("\nDebug - PR State Changes:")
            print(f"Previously Open: {self.previously_open_prs}")
            print(f"Previously Closed: {self.previously_closed_prs}")
            print(f"Current Open: {current_open_prs}")
            print(f"Current Closed: {current_closed_prs}")
            print(f"Disappeared from Open: {disappeared_from_open}")
            print(f"Newly Closed: {newly_closed}")
            print(f"New PRs: {new_prs}")
            print(f"Reopened PRs: {reopened_prs}")
            
            # Send notifications for changes
            if newly_closed:
                closed_details = []
                for pr_num in newly_closed:
                    if pr := pr_objects.get(pr_num):
                        repo = f"{pr.repo_owner}/{pr.repo_name}"
                        author = pr.user.login if pr.user else "Unknown"
                        closed_details.append(f"#{pr_num} - {pr.title}\nRepo: {repo}\nAuthor: {author}")
                
                if closed_details:
                    notify("GitHub PR Watcher", "Recently closed PRs:\n" + "\n\n".join(closed_details))
            
            # Update tracking sets after notifications
            self.previously_open_prs = current_open_prs.copy()
            self.previously_closed_prs = current_closed_prs.copy()
        
        # Update user filter before updating sections
        self.update_user_filter()
        
        # Update sections
        self._update_section(self.needs_review_frame, prs_awaiting_review_by_user)
        self._update_section(self.changes_requested_frame, prs_that_need_attention_by_user)
        self._update_section(self.open_prs_frame, open_prs_by_user)
        self._update_section(self.recently_closed_frame, user_recently_closed_prs_by_user)

    def _update_section(self, frame, prs):
        """Update a section with new PR data"""
        try:
            # Clear existing content
            if frame.content_layout:
                for i in reversed(range(frame.content_layout.count())):
                    item = frame.content_layout.itemAt(i)
                    if item and item.widget():
                        item.widget().deleteLater()
            
            # Store the PR data in the frame (store complete data)
            frame.prs = prs
            
            # Filter PRs based on section type first
            section_filters = {
                "Open PRs": lambda pr: str(getattr(pr, 'state', '')).lower() == 'open',
                "Recently Closed": lambda pr: (
                    getattr(pr, 'merged_at', None) is not None or  # Check merged first
                    str(getattr(pr, 'state', '')).lower() in ['closed', str(TimelineEventType.CLOSED).lower()] or 
                    getattr(pr, 'closed_at', None) is not None
                ),
                "Needs Review": lambda pr: True,  # Already filtered by GitHub query
                "Changes Requested": lambda pr: True,  # Already filtered by GitHub query
            }
            
            # Apply section-specific filter
            section_filter = section_filters.get(frame.title, lambda pr: True)
            
            print(f"\nDebug - Processing section: {frame.title}")
            print(f"Debug - Initial PR count: {sum(len(user_prs) for user_prs in prs.values())}")
            
            # Filter PRs based on draft visibility and user filter
            show_drafts = self.show_drafts_toggle.isChecked()
            selected_users = self.user_filter.getSelectedItems()
            
            filtered_prs = {}
            total_prs = 0
            for user, user_prs in prs.items():
                # Apply user filter
                if "All Authors" not in selected_users and user not in selected_users:
                    continue
                
                # Apply section filter and draft filter
                filtered_user_prs = []
                for pr in user_prs:
                    state = str(getattr(pr, 'state', '')).lower()
                    merged = getattr(pr, 'merged_at', None) is not None
                    closed = getattr(pr, 'closed_at', None) is not None
                    print(f"Debug - PR #{pr.number} - State: {state}, Merged: {merged}, Closed: {closed}")
                    
                    if section_filter(pr) and (show_drafts or not getattr(pr, 'draft', False)):
                        filtered_user_prs.append(pr)
                
                if filtered_user_prs:
                    filtered_prs[user] = filtered_user_prs
                    total_prs += len(filtered_user_prs)
            
            print(f"Debug - After filtering - Total PRs: {total_prs}")
            
            # Update count
            frame.update_count(total_prs)
            
            is_empty = not filtered_prs
            if is_empty:
                label = QLabel("No PRs to display")
                frame.content_layout.addWidget(label)
                # Auto-collapse if empty
                if frame.is_expanded:
                    frame.toggle_content()
                return
            
            # Auto-expand if not empty and was collapsed
            if not frame.is_expanded:
                frame.toggle_content()
            
            # Add PR cards based on grouping preference
            if self.group_by_user_toggle.isChecked():
                # Group by user
                for user, user_prs in filtered_prs.items():
                    # Create user header container
                    user_header_container = QWidget()
                    user_header_layout = QHBoxLayout(user_header_container)
                    user_header_layout.setContentsMargins(0, 5, 0, 5)
                    user_header_layout.setSpacing(5)
                    
                    # Add user name
                    user_label = QLabel(f"@{user}")
                    user_label.setStyleSheet("""
                        QLabel {
                            color: #8b949e;
                            font-size: 12px;
                            font-weight: bold;
                        }
                    """)
                    user_header_layout.addWidget(user_label)
                    
                    # Add PR count
                    count_label = QLabel(f"({len(user_prs)})")
                    count_label.setStyleSheet("""
                        QLabel {
                            color: #8b949e;
                            font-size: 11px;
                        }
                    """)
                    user_header_layout.addWidget(count_label)
                    
                    # Add stretch to push everything to the left
                    user_header_layout.addStretch()
                    
                    frame.content_layout.addWidget(user_header_container)
                    
                    # Add user's PR cards
                    for pr in user_prs:
                        try:
                            card = create_pr_card(pr, self.settings)
                            frame.content_layout.addWidget(card)
                        except Exception as e:
                            print(f"Warning: Error creating PR card: {e}")
                            continue
                    
                    # Add spacer after each user group except the last
                    if user != list(filtered_prs.keys())[-1]:
                        spacer = QFrame()
                        spacer.setStyleSheet("background-color: #404040; margin: 10px 0;")
                        spacer.setFixedHeight(1)
                        frame.content_layout.addWidget(spacer)
            else:
                # Flat list of PRs
                for user, user_prs in filtered_prs.items():
                    for pr in user_prs:
                        try:
                            card = create_pr_card(pr, self.settings)
                            frame.content_layout.addWidget(card)
                        except Exception as e:
                            print(f"Warning: Error creating PR card: {e}")
                            continue
                        
        except Exception as e:
            print(f"Error updating section: {e}")

    def toggle_user_grouping(self):
        """Toggle user grouping without refreshing"""
        # Re-render all sections with current data
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame
        ]:
            self._update_section(frame, frame.prs)

    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                settings = dialog.get_settings()
                
                # Store current PR data before updating settings
                current_data = (
                    self.open_prs_frame.prs,
                    self.needs_review_frame.prs,
                    self.changes_requested_frame.prs,
                    self.recently_closed_frame.prs
                )
                
                # Get current settings before updating
                current_settings = load_settings()
                
                # Save new settings first
                save_settings(settings)
                self.settings = settings  # Update settings in memory
                
                # Compare refresh settings
                old_refresh = current_settings.get('refresh', {})
                new_refresh = settings.get('refresh', {})
                if (old_refresh.get('value') != new_refresh.get('value') or 
                    old_refresh.get('unit') != new_refresh.get('unit')):
                    print("\nDebug - Refresh settings changed:")
                    print(f"  Old: {old_refresh.get('value')} {old_refresh.get('unit')}")
                    print(f"  New: {new_refresh.get('value')} {new_refresh.get('unit')}")
                    # Stop current timer
                    if hasattr(self, 'auto_refresh_timer'):
                        self.auto_refresh_timer.stop()
                    # Setup new timer with new settings
                    self.setup_refresh_timer(new_refresh)
                
                # Compare users and cache settings
                if (settings.get('users') != current_settings.get('users', []) or 
                    settings.get('cache') != current_settings.get('cache', {})):
                    print("\nDebug - Users or cache settings changed, triggering immediate refresh...")
                    self.refresh_data()
                else:
                    # Even if only thresholds changed, update the UI to reflect new colors/badges
                    print("\nDebug - Updating UI with new thresholds...")
                    self.update_pr_lists(*current_data)
                
        except Exception as e:
            print(f"Error showing settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show settings: {str(e)}")

    def setup_refresh_timer(self, refresh_settings=None):
        """Setup the refresh timer"""
        try:
            if not refresh_settings:
                refresh_settings = self.settings.get('refresh', {'value': 30, 'unit': 'minutes'})
            
            value = refresh_settings['value']
            unit = refresh_settings['unit']
            
            # Convert to milliseconds
            if unit == 'seconds':
                interval = value * 1000
            elif unit == 'minutes':
                interval = value * 60 * 1000
            else:  # hours
                interval = value * 60 * 60 * 1000
                
            print(f"Debug - Setting up refresh timer with interval: {interval}ms ({value} {unit})")
            
            # Stop existing timer if it exists
            if hasattr(self, 'auto_refresh_timer'):
                self.auto_refresh_timer.stop()
                print("Debug - Stopped existing timer")
            
            # Create and start new timer
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.refresh_data)
            self.auto_refresh_timer.start(interval)
            print("Debug - Started new timer")
            
        except Exception as e:
            print(f"Error setting up refresh timer: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep loading overlay centered
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.centralWidget().rect())

    def toggle_drafts_visibility(self):
        """Toggle visibility of draft PRs without refreshing"""
        # Re-render all sections with current data
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame
        ]:
            self._update_section(frame, frame.prs)

    def update_user_filter(self):
        """Update user filter dropdown with users from settings"""
        current_text = self.user_filter.currentText()
        self.user_filter.clear()
        self.user_filter.addItem("All Authors")
        
        # Get users from settings
        users = sorted(self.settings.get('users', []))
        
        # Add users to dropdown
        for user in users:
            self.user_filter.addItem(user)
        
        # Restore previous selection if it still exists
        index = self.user_filter.findText(current_text)
        if index >= 0:
            self.user_filter.setCurrentIndex(index)
        else:
            self.user_filter.setCurrentIndex(0)  # Default to "All Authors"

    def apply_filters(self):
        """Apply all filters (drafts, grouping, user) to the UI without refreshing data"""
        # Re-render all sections with current filters using existing data
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame
        ]:
            self._update_section(frame, frame.prs)

    def rotate_spinner(self):
        """Rotate the spinner icon"""
        if not hasattr(self, 'spinner_rotation'):
            self.spinner_rotation = 0
        
        self.spinner_rotation = (self.spinner_rotation + 30) % 360
        self.spinner_label.setStyleSheet(f"""
            QLabel {{
                color: #0d6efd;
                font-size: 16px;
                padding: 0 5px;
                transform: rotate({self.spinner_rotation}deg);
            }}
        """)

    def cleanup_worker(self, worker=None):
        """Clean up a single worker"""
        if worker is None:
            worker = self.refresh_worker
            
        if worker:
            worker.quit()
            worker.wait()
            if worker in self.workers:
                self.workers.remove(worker)
            if worker == self.refresh_worker:
                self.refresh_worker = None
            print("Debug - Cleaned up worker")

    def cleanup_workers(self):
        """Clean up all workers"""
        # Clean up refresh worker
        if self.refresh_worker:
            self.cleanup_worker(self.refresh_worker)
        
        # Clean up any other workers
        for worker in self.workers[:]:  # Create a copy of the list to avoid modification during iteration
            self.cleanup_worker(worker)
        self.workers.clear()
        print("Debug - Cleaned up all workers")


def open_ui(open_prs_by_user, prs_awaiting_review_by_user,
            prs_that_need_attention_by_user, user_recently_closed_prs_by_user,
            github_prs=None, settings=None):
    app = QApplication([])
    app.setStyle('Fusion')
    
    window = PRWatcherUI()
    
    # Use passed settings or load them
    if settings is None:
        settings = load_settings()
    window.settings = settings
    
    window.consecutive_failures = 0
    window.max_backoff = 5
    
    # Use passed GitHubPRs instance or create new one
    if github_prs is None:
        github_token = get_github_api_key()
        cache_duration = settings.get('cache_duration', 1)
        github_prs = GitHubPRs(
            github_token,
            recency_threshold=timedelta(days=1),
            cache_dir=".cache",
            cache_ttl=timedelta(hours=cache_duration)
        )
    window.github_prs = github_prs
    
    # Initialize user filter before updating PR lists
    window.update_user_filter()
    
    # Update initial data
    window.update_pr_lists(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user
    )
    
    # Initialize refresh timer with current settings
    window.setup_refresh_timer(settings.get('refresh'))
    
    window.show()
    
    return app.exec()


def get_changes_color(total_changes, settings):
    """Calculate gradient color based on number of changes"""
    warning_level = settings.get('thresholds', {}).get('lines', {}).get('warning', 500)
    danger_level = settings.get('thresholds', {}).get('lines', {}).get('danger', 1000)
    
    if total_changes <= warning_level:
        return "rgba(40, 167, 69, 0.5)"  # Green with 0.5 opacity
    elif total_changes <= danger_level:
        # Calculate position between warning and danger
        ratio = (total_changes - warning_level) / (danger_level - warning_level)
        # Create a gradient from green to yellow to red
        if ratio <= 0.5:
            # Green to yellow
            return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, " \
                   f"stop:0 rgba(40, 167, 69, 0.5), " \
                   f"stop:1 rgba(255, 193, 7, 0.5))"
        else:
            # Yellow to red
            return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, " \
                   f"stop:0 rgba(255, 193, 7, 0.5), " \
                   f"stop:1 rgba(220, 53, 69, 0.5))"
    else:
        return "rgba(220, 53, 69, 0.5)"  # Red with 0.5 opacity

def create_changes_badge(additions, deletions, settings):
    """Create a badge showing additions and deletions with color gradient"""
    total_changes = additions + deletions
    bg_color = get_changes_color(total_changes, settings)
    
    changes_badge = QFrame()
    changes_badge.setStyleSheet(f"""
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
    """)
    
    layout = QHBoxLayout(changes_badge)
    layout.setContentsMargins(6, 0, 6, 0)
    layout.setSpacing(4)
    
    # Show additions in green text
    additions_label = QLabel(f"+{additions}")
    additions_label.setStyleSheet("color: rgba(152, 255, 152, 0.9); font-size: 10px; font-weight: bold;")
    layout.addWidget(additions_label)
    
    # Separator
    separator = QLabel("/")
    separator.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 10px;")
    layout.addWidget(separator)
    
    # Show deletions in red text
    deletions_label = QLabel(f"-{deletions}")
    deletions_label.setStyleSheet("color: rgba(255, 179, 179, 0.9); font-size: 10px; font-weight: bold;")
    layout.addWidget(deletions_label)
    
    return changes_badge

def load_settings():
    """Load settings from YAML file"""
    settings_file = os.path.expanduser('~/.github-pr-watcher.yml')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading settings: {e}")
    return {}

def save_settings(settings):
    """Save settings to YAML file"""
    settings_file = os.path.expanduser('~/.github-pr-watcher.yml')
    try:
        with open(settings_file, 'w') as f:
            yaml.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings: {e}")