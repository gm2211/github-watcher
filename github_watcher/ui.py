from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QDialog,
    QLineEdit, QSpinBox, QFormLayout, QTextEdit, QGroupBox, QComboBox,
    QTabWidget, QDialogButtonBox, QPlainTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QTransform
import webbrowser
from datetime import datetime, timezone, timedelta
import platform
import os
from notifications import notify, NOTIFIER_APP
import yaml
import time
from github_auth import get_github_api_key
from github_prs import GitHubPRs
from objects import TimelineEventType


class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.title = title  # Store title as instance variable
        self.prs = {}  # Initialize prs attribute
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
        
        # Title label
        self.title_label = QLabel(self.title)  # Use stored title
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        self.left_layout.addWidget(self.title_label)
        
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
        if not self.spinner_label or not self.is_loading:
            return
            
        self.spinner_rotation = (self.spinner_rotation + 30) % 360
        self.spinner_label.setStyleSheet(f"""
            QLabel {{
                color: #0d6efd;
                font-size: 14px;
                padding: 0 5px;
                transform: rotate({self.spinner_rotation}deg);
            }}
        """)


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
    
    # Draft badge check
    is_draft = getattr(pr_data, 'draft', None)
    print(f"  Draft status check:")
    print(f"    - draft attribute: {is_draft}")
    print(f"    - type: {type(is_draft)}")
    
    if is_draft:
        print("    - Adding DRAFT badge")
        draft_badge = create_badge("DRAFT", "#6c757d", opacity=1.0)  # Gray
        right_badges.addWidget(draft_badge)
    
    # Check for review status in timeline
    if timeline := getattr(pr_data, 'timeline', []):
        print(f"  Processing {len(timeline)} timeline events:")
        latest_review_state = None
        latest_review_author = None
        
        # Go through events from newest to oldest
        for event in reversed(timeline):
            print(f"    - Event: {event.eventType}")
            if event.eventType == TimelineEventType.APPROVED:
                latest_review_state = TimelineEventType.APPROVED
                latest_review_author = event.author.login if event.author else None
                print(f"      Found approval by {latest_review_author}")
                break
            elif event.eventType == TimelineEventType.CHANGES_REQUESTED:
                latest_review_state = TimelineEventType.CHANGES_REQUESTED
                latest_review_author = event.author.login if event.author else None
                print(f"      Found changes requested by {latest_review_author}")
                break
        
        print(f"  Final review state: {latest_review_state}")
        print(f"  Review author: {latest_review_author}")
        
        if latest_review_state == TimelineEventType.APPROVED:
            approved_text = "APPROVED"
            if latest_review_author:
                approved_text += f" by {latest_review_author}"
            print(f"    Adding approval badge: {approved_text}")
            approved_badge = create_badge(approved_text, "#28a745", opacity=1.0)  # Green
            right_badges.addWidget(approved_badge)
        elif latest_review_state == TimelineEventType.CHANGES_REQUESTED:
            changes_text = "CHANGES REQUESTED"
            if latest_review_author:
                changes_text += f" by {latest_review_author}"
            print(f"    Adding changes requested badge: {changes_text}")
            changes_badge = create_badge(changes_text, "#dc3545", opacity=1.0)  # Red
            right_badges.addWidget(changes_badge)
    
    # Status badge colors
    MERGED_COLOR = "#6f42c1"  # Purple
    CLOSED_COLOR = "#dc3545"  # Red
    OPEN_COLOR = "#28a745"    # Green
    
    if getattr(pr_data, 'merged_at', None):
        status_badge = create_badge("MERGED", MERGED_COLOR, opacity=1.0)
    elif getattr(pr_data, 'state', '') == 'closed':
        status_badge = create_badge("CLOSED", CLOSED_COLOR, opacity=1.0)
    else:
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
        self.setup_ui()
        self.load_settings()

    def get_settings(self):
        """Get current settings values"""
        return {
            'thresholds': {
                'additions': {
                    'warning': self.additions_warning.value(),
                    'danger': self.additions_danger.value()
                },
                'deletions': {
                    'warning': self.deletions_warning.value(),
                    'danger': self.deletions_danger.value()
                },
                'files': {
                    'warning': self.files_warning.value(),
                    'danger': self.files_danger.value()
                }
            },
            'cache': {
                'value': self.cache_value.value(),
                'unit': self.cache_unit.currentText()
            },
            'refresh': {
                'value': self.refresh_value.value(),
                'unit': self.refresh_unit.currentText()
            },
            'users': [u.strip() for u in self.users_text.toPlainText().split('\n') if u.strip()]
        }

    def accept(self):
        """Handle dialog acceptance"""
        try:
            self.save_settings()
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def load_settings(self):
        """Load settings from file"""
        settings = load_settings()
        
        # Load thresholds
        thresholds = settings.get('thresholds', {})
        
        # Additions thresholds
        additions = thresholds.get('additions', {})
        self.additions_warning.setValue(additions.get('warning', 300))
        self.additions_danger.setValue(additions.get('danger', 1000))
        
        # Deletions thresholds
        deletions = thresholds.get('deletions', {})
        self.deletions_warning.setValue(deletions.get('warning', 1000))
        self.deletions_danger.setValue(deletions.get('danger', 10000))
        
        # Files thresholds
        files = thresholds.get('files', {})
        self.files_warning.setValue(files.get('warning', 10))
        self.files_danger.setValue(files.get('danger', 50))
        
        # Load cache settings
        cache = settings.get('cache', {})
        self.cache_value.setValue(cache.get('value', 1))
        self.cache_unit.setCurrentText(cache.get('unit', 'hours'))
        
        # Load refresh settings
        refresh = settings.get('refresh', {})
        self.refresh_value.setValue(refresh.get('value', 30))
        self.refresh_unit.setCurrentText(refresh.get('unit', 'minutes'))
        
        # Load users
        users = settings.get('users', [])
        self.users_text.setPlainText('\n'.join(users))

    def save_settings(self):
        """Save settings to file"""
        settings = {
            'thresholds': {
                'additions': {
                    'warning': self.additions_warning.value(),
                    'danger': self.additions_danger.value()
                },
                'deletions': {
                    'warning': self.deletions_warning.value(),
                    'danger': self.deletions_danger.value()
                },
                'files': {
                    'warning': self.files_warning.value(),
                    'danger': self.files_danger.value()
                }
            },
            'cache': {
                'value': self.cache_value.value(),
                'unit': self.cache_unit.currentText()
            },
            'refresh': {
                'value': self.refresh_value.value(),
                'unit': self.refresh_unit.currentText()
            },
            'users': [u.strip() for u in self.users_text.toPlainText().split('\n') if u.strip()]
        }
        
        save_settings(settings)

    def setup_ui(self):
        """Setup the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Thresholds tab
        thresholds_tab = QWidget()
        thresholds_layout = QFormLayout(thresholds_tab)
        
        # Additions thresholds
        self.additions_warning = QSpinBox()
        self.additions_warning.setMaximum(10000)
        self.additions_danger = QSpinBox()
        self.additions_danger.setMaximum(10000)
        thresholds_layout.addRow("Additions Warning:", self.additions_warning)
        thresholds_layout.addRow("Additions Danger:", self.additions_danger)
        
        # Deletions thresholds
        self.deletions_warning = QSpinBox()
        self.deletions_warning.setMaximum(100000)
        self.deletions_danger = QSpinBox()
        self.deletions_danger.setMaximum(100000)
        thresholds_layout.addRow("Deletions Warning:", self.deletions_warning)
        thresholds_layout.addRow("Deletions Danger:", self.deletions_danger)
        
        # Files thresholds
        self.files_warning = QSpinBox()
        self.files_warning.setMaximum(1000)
        self.files_danger = QSpinBox()
        self.files_danger.setMaximum(1000)
        thresholds_layout.addRow("Files Warning:", self.files_warning)
        thresholds_layout.addRow("Files Danger:", self.files_danger)
        
        tabs.addTab(thresholds_tab, "Thresholds")
        
        # Cache and Refresh tab
        timing_tab = QWidget()
        timing_layout = QFormLayout(timing_tab)
        
        # Cache settings
        cache_widget = QWidget()
        cache_layout = QHBoxLayout(cache_widget)
        self.cache_value = QSpinBox()
        self.cache_value.setMaximum(24)
        self.cache_unit = QComboBox()
        self.cache_unit.addItems(['seconds', 'minutes', 'hours'])
        cache_layout.addWidget(self.cache_value)
        cache_layout.addWidget(self.cache_unit)
        timing_layout.addRow("Cache Duration:", cache_widget)
        
        # Refresh settings
        refresh_widget = QWidget()
        refresh_layout = QHBoxLayout(refresh_widget)
        self.refresh_value = QSpinBox()
        self.refresh_value.setMaximum(60)
        self.refresh_unit = QComboBox()
        self.refresh_unit.addItems(['seconds', 'minutes', 'hours'])
        refresh_layout.addWidget(self.refresh_value)
        refresh_layout.addWidget(self.refresh_unit)
        timing_layout.addRow("Refresh Interval:", refresh_widget)
        
        tabs.addTab(timing_tab, "Timing")
        
        # Users tab
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        self.users_text = QPlainTextEdit()
        users_layout.addWidget(QLabel("Users (one per line):"))
        users_layout.addWidget(self.users_text)
        tabs.addTab(users_tab, "Users")
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def load_settings():
    settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.yaml')
    
    if not os.path.exists(settings_file):
        # Default settings
        settings = {
            'users': [],
            'refresh': {
                'value': 10,
                'unit': 'seconds'
            },
            'cache': {
                'value': 1,
                'unit': 'hours'
            },
            'thresholds': {
                'files': {
                    'warning': 10,
                    'danger': 50
                },
                'lines': {
                    'warning': 500,
                    'danger': 1000
                }
            }
        }
        
        save_settings(settings)
        return settings
    
    try:
        with open(settings_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}


def save_settings(settings):
    settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.yaml')
    try:
        with open(settings_file, 'w') as f:
            yaml.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings: {e}")


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


class PRWatcherUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub PR Watcher")
        
        # Set window icon
        try:
            if platform.system() == "Darwin":
                current_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(current_dir, "gh_notify.app/Contents/Resources/applet.icns")
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Could not set icon: {e}")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create header with buttons
        header_layout = QHBoxLayout()
        
        # Left side: spinner and title
        left_layout = QHBoxLayout()
        
        # Spinner
        self.spinner_label = QLabel("⟳")
        self.spinner_label.setFixedWidth(20)
        self.spinner_label.setStyleSheet("""
            QLabel {
                color: #0d6efd;
                font-size: 16px;
                padding: 0 5px;
            }
        """)
        self.spinner_label.hide()  # Hidden by default
        left_layout.addWidget(self.spinner_label)
        
        # Initialize spinner rotation and timer
        self.spinner_rotation = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.rotate_spinner)
        self.spinner_timer.setInterval(50)  # 50ms for smoother rotation
        
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
        
        # Add draft toggle after title
        self.show_drafts_toggle = QPushButton("Hide Drafts")
        self.show_drafts_toggle.setCheckable(True)
        self.show_drafts_toggle.setChecked(True)  # Show drafts by default
        self.show_drafts_toggle.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
                font-size: 12px;
                height: 25px;
            }
            QPushButton:checked {
                background-color: #0d6efd;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.show_drafts_toggle.clicked.connect(self.toggle_drafts_visibility)
        left_layout.addWidget(self.show_drafts_toggle)
        
        # Create section frames (remove draft section)
        self.needs_review_frame = SectionFrame("Needs Review")
        self.changes_requested_frame = SectionFrame("Changes Requested")
        self.open_prs_frame = SectionFrame("Open PRs")
        self.recently_closed_frame = SectionFrame("Recently Closed")
        
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
        notify(NOTIFIER_APP, "GitHub PR Watcher", "Test notification - System is working!")

    def refresh_data(self):
        # Clean up any existing workers
        self.cleanup_workers()
            
        print("\nDebug - Starting refresh...")
        self.spinner_label.show()
        self.spinner_timer.start()
        self.progress_label.show()
        self.progress_label.setText("Starting refresh...")
        
        # Reset loading sections and start loading animations
        self.loading_sections = {}
        for frame in [self.open_prs_frame, self.needs_review_frame, 
                     self.changes_requested_frame, self.recently_closed_frame]:
            frame.start_loading()
        
        # Create and start worker threads for each section
        sections = ['draft', 'review', 'open', 'attention', 'closed']
        for section in sections:
            worker = RefreshWorker(self.github_prs, self.settings.get('users', []), section)
            worker.finished.connect(lambda data, s=section: self.handle_section_refresh(s, data))
            worker.error.connect(self.handle_refresh_error)
            worker.progress.connect(self.update_progress)
            worker.finished.connect(lambda _, w=worker: self.cleanup_worker(w))
            worker.error.connect(lambda _, w=worker: self.cleanup_worker(w))
            self.workers.append(worker)
            worker.start()

    def update_progress(self, message):
        """Update progress message"""
        self.progress_label.setText(message)

    def cleanup_worker(self, worker):
        """Clean up a single worker"""
        if worker in self.workers:
            worker.quit()
            worker.wait()
            self.workers.remove(worker)
            print(f"Debug - Cleaned up worker (remaining: {len(self.workers)})")
            
            # If this was the last worker, hide the spinner and progress
            if not self.workers:
                self.spinner_label.hide()
                self.spinner_timer.stop()
                self.progress_label.hide()
                self.progress_label.setText("")

    def cleanup_workers(self):
        """Clean up all workers"""
        for worker in self.workers[:]:  # Create a copy of the list to avoid modification during iteration
            self.cleanup_worker(worker)
        self.workers.clear()
        print("Debug - Cleaned up all workers")

    def handle_section_refresh(self, section, data):
        """Handle refresh completion for a specific section"""
        print(f"Debug - Section {section} refresh completed")
        
        # Map sections to frames and their filtering logic
        section_map = {
            'open': (self.open_prs_frame, lambda pr: (
                getattr(pr, 'state', '') == 'open' and 
                not getattr(pr, 'merged_at', None) and 
                (self.show_drafts_toggle.isChecked() or not getattr(pr, 'draft', False))
            )),
            'review': (self.needs_review_frame, lambda pr: True),
            'attention': (self.changes_requested_frame, lambda pr: True),
            'closed': (self.recently_closed_frame, lambda pr: getattr(pr, 'state', '') == 'closed' or getattr(pr, 'merged_at', None))
        }
        
        if section in section_map:
            frame, filter_func = section_map[section]
            
            # Get the section-specific data from the correct tuple index
            section_indices = {'open': 0, 'review': 1, 'attention': 2, 'closed': 3}
            section_data = data[section_indices[section]]
            
            print(f"Debug - Processing {section} data with {sum(len(prs) for prs in section_data.values() if isinstance(prs, list))} PRs")
            
            # Apply section-specific filtering
            filtered_data = {
                user: [pr for pr in prs if filter_func(pr)]
                for user, prs in section_data.items()
            }
            
            # Remove empty user entries
            filtered_data = {user: prs for user, prs in filtered_data.items() if prs}
            
            # Update the frame with filtered data
            print(f"Debug - Updating {section} section with {sum(len(prs) for prs in filtered_data.values())} filtered PRs")
            self._update_section(frame, filtered_data)
            
            # Store the filtered data
            frame.prs = filtered_data
            
            # Stop loading animation
            frame.stop_loading()

    def handle_refresh_error(self, error_msg):
        print(f"Error refreshing data: {error_msg}")
        self.consecutive_failures += 1
        print(f"Consecutive failures: {self.consecutive_failures}")

    def closeEvent(self, event):
        # Clean up all workers when closing
        self.cleanup_workers()
        super().closeEvent(event)

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
                    notify(NOTIFIER_APP, "PRs Closed", 
                          "Recently closed PRs:\n" + "\n\n".join(closed_details))
            
            # Update tracking sets after notifications
            self.previously_open_prs = current_open_prs.copy()
            self.previously_closed_prs = current_closed_prs.copy()
        
        # Update UI
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
            
            # Filter PRs based on draft visibility
            show_drafts = self.show_drafts_toggle.isChecked()
            filtered_prs = {}
            for user, user_prs in prs.items():
                filtered_user_prs = [
                    pr for pr in user_prs 
                    if show_drafts or not getattr(pr, 'draft', False)
                ]
                if filtered_user_prs:
                    filtered_prs[user] = filtered_user_prs
            
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
            
            # Add PR cards for filtered PRs
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

    def rotate_spinner(self):
        self.spinner_rotation = (self.spinner_rotation + 30) % 360
        transform = QTransform()
        transform.rotate(self.spinner_rotation)
        self.spinner_label.setStyleSheet(f"""
            QLabel {{
                color: #0d6efd;
                font-size: 16px;
                padding: 0 5px;
            }}
        """)
        # Use Qt's transform property for smoother rotation
        self.spinner_label.setProperty("rotation", self.spinner_rotation)
        self.spinner_label.style().unpolish(self.spinner_label)
        self.spinner_label.style().polish(self.spinner_label)

    def toggle_drafts_visibility(self):
        """Toggle visibility of draft PRs without refreshing"""
        # Update toggle button text
        show_drafts = self.show_drafts_toggle.isChecked()
        self.show_drafts_toggle.setText("Hide Drafts" if show_drafts else "Show Drafts")
        
        # Re-render all sections with current data
        for frame in [
            self.open_prs_frame,
            self.needs_review_frame,
            self.changes_requested_frame,
            self.recently_closed_frame
        ]:
            self._update_section(frame, frame.prs)


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