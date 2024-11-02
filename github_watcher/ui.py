from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QDialog,
    QLineEdit, QSpinBox, QFormLayout, QTextEdit, QGroupBox, QComboBox,
    QTabWidget, QDialogButtonBox, QPlainTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
import webbrowser
from datetime import datetime, timezone, timedelta
import platform
import os
from notifications import notify, NOTIFIER_APP
import yaml
import time
from github_auth import get_github_api_key
from github_prs import GitHubPRs


class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.prs = {}  # Initialize prs attribute
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
        
        # Header container
        header_container = QFrame()
        header_container.setFixedHeight(30)
        header_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)
        
        # Left side of header (title and toggle)
        left_header = QWidget()
        left_header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        left_layout = QHBoxLayout(left_header)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        left_layout.addWidget(self.title_label)
        
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
        left_layout.addWidget(self.toggle_button)
        left_layout.addStretch()
        
        header_layout.addWidget(left_header)
        self.main_layout.addWidget(header_container)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2d2d2d;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Content container inside scroll area
        self.content_container = QWidget()
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.content_container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 5, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_container)
        self.main_layout.addWidget(self.scroll_area)
        
        # Make header clickable
        header_container.mousePressEvent = self.toggle_content
        header_container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Start collapsed
        self.is_expanded = True
        self.toggle_content()
    
    def toggle_content(self, event=None):
        self.is_expanded = not self.is_expanded
        self.scroll_area.setVisible(self.is_expanded)
        self.toggle_button.setText("▼" if self.is_expanded else "▶")
        
        # Update minimum height based on state
        if self.is_expanded:
            self.setMinimumHeight(0)
        else:
            self.setMinimumHeight(50)  # Just enough for header
    
    def set_empty(self, is_empty):
        """Collapse section if empty"""
        if is_empty and self.is_expanded:
            self.toggle_content()
    
    def layout(self):
        return self.content_layout


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
    header = QHBoxLayout()
    header.setSpacing(8)
    
    # Title with PR number
    title_text = f"{getattr(pr_data, 'title', 'Untitled')} (#{getattr(pr_data, 'number', '?')})"
    title = QLabel(title_text)
    title.setFont(QFont("", 13, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff; text-decoration: underline; background: transparent;")
    title.setCursor(Qt.CursorShape.PointingHandCursor)
    
    # Create a proper event handler for the click
    if url := getattr(pr_data, 'html_url', None):
        def open_url(event):
            webbrowser.open(url)
        title.mousePressEvent = open_url
    
    header.addWidget(title)
    
    # Add repo info
    repo_text = f"{pr_data.repo_owner}/{pr_data.repo_name}"
    repo_label = QLabel(repo_text)
    repo_label.setStyleSheet("color: #8b949e; font-size: 11px; background: transparent;")
    header.addWidget(repo_label)
    
    # Badges
    badges_layout = QHBoxLayout()
    badges_layout.setSpacing(4)
    
    # Left side badges (files and changes)
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
        badges_layout.addWidget(files_badge)
    
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
        badges_layout.addWidget(changes_badge)
    
    badges_layout.addStretch()  # Push status badges to the right
    
    # Right side badges container
    right_badges = QHBoxLayout()
    right_badges.setSpacing(4)
    
    # Status badges (full opacity)
    if getattr(pr_data, 'draft', False):
        draft_badge = create_badge("DRAFT", "#6c757d", opacity=1.0)  # Gray
        right_badges.addWidget(draft_badge)
    
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
    
    # Add right badges to main badges layout
    badges_layout.addLayout(right_badges)
    
    # Add badges layout to header
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
    
    # Create a container for all info items
    info_items = QFrame()
    info_items_layout = QVBoxLayout(info_items)
    info_items_layout.setContentsMargins(0, 0, 0, 0)
    info_items_layout.setSpacing(1)  # Minimal spacing between items
    
    # Author info
    user = getattr(pr_data, 'user', None)
    if user and hasattr(user, 'login'):
        author_text = f"Author: {user.login}"
        author_label = QLabel(author_text)
        author_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
        info_items_layout.addWidget(author_label)
    
    # Comments info
    timeline = getattr(pr_data, 'timeline', [])
    if timeline:
        comments = [event for event in timeline if 'comments' in getattr(event, 'url', '')]
        comments_count = len(comments)
        if comments_count > 0:
            comments_text = f"💬 {comments_count} comment{'s' if comments_count != 1 else ''}"
            comments_label = QLabel(comments_text)
            comments_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
            info_items_layout.addWidget(comments_label)
            
            latest_comment = comments[-1]
            if latest_comment:
                comment_author = getattr(latest_comment.author, 'login', 'Unknown')
                comment_date = getattr(latest_comment, 'created_at', None)
                
                if comment_date:
                    now = datetime.now(timezone.utc)
                    time_diff = now - comment_date
                    time_text = format_time_diff(time_diff)
                    last_comment_text = f"Last comment by {comment_author} {time_text}"
                    last_comment_label = QLabel(last_comment_text)
                    last_comment_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0;")
                    info_items_layout.addWidget(last_comment_label)
    
    left_info.addWidget(info_items)
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
    
    def __init__(self, github_prs, users):
        super().__init__()
        self.github_prs = github_prs
        self.users = users
        
    def run(self):
        try:
            print("\nDebug - Worker: Fetching fresh PR data...")
            new_data = self.github_prs.get_pr_data(self.users, force_refresh=True)
            if new_data is not None:
                self.finished.emit(new_data)
            else:
                self.error.emit("Refresh failed, no data returned")
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
        
        # Title
        title = QLabel("GitHub PR Watcher")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
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
        
        # Create section frames
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
        
        # Set up auto-refresh timer
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        
        # Load settings and set initial refresh interval
        self.settings = load_settings()
        refresh_value = self.settings.get('refresh', {}).get('value', 10)
        refresh_unit = self.settings.get('refresh', {}).get('unit', 'seconds')
        
        if refresh_unit == 'minutes':
            refresh_ms = refresh_value * 60 * 1000
        else:  # seconds
            refresh_ms = refresh_value * 1000
        
        self.auto_refresh_timer.start(refresh_ms)
        
        # Initialize tracking for PRs with empty sets
        self.previously_open_prs = set()
        self.previously_closed_prs = set()
        self.notified_prs = set()
        self.initial_state = True  # Add flag for initial state
        
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
        
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(central_widget)
        self.loading_overlay.hide()
        
        # Initialize worker to None
        self.refresh_worker = None
        self.consecutive_failures = 0
        self.max_backoff = 5
    
    def show_test_notification(self):
        notify(NOTIFIER_APP, "GitHub PR Watcher", "Test notification - System is working!")

    def refresh_data(self):
        if self.refresh_worker and self.refresh_worker.isRunning():
            print("Debug - Refresh already in progress, skipping")
            return
            
        print("\nDebug - Starting refresh...")
        self.loading_overlay.show()
        
        # Create and start worker thread
        self.refresh_worker = RefreshWorker(self.github_prs, self.settings.get('users', []))
        self.refresh_worker.finished.connect(self.handle_refresh_success)
        self.refresh_worker.error.connect(self.handle_refresh_error)
        self.refresh_worker.finished.connect(self.cleanup_worker)
        self.refresh_worker.error.connect(self.cleanup_worker)
        self.refresh_worker.start()

    def handle_refresh_success(self, new_data):
        print("Debug - Refresh completed successfully")
        self.update_pr_lists(*new_data)
        self.consecutive_failures = 0
        self.loading_overlay.hide()

    def handle_refresh_error(self, error_msg):
        print(f"Error refreshing data: {error_msg}")
        self.consecutive_failures += 1
        print(f"Consecutive failures: {self.consecutive_failures}")
        self.loading_overlay.hide()

    def cleanup_worker(self):
        if self.refresh_worker:
            self.refresh_worker.quit()
            self.refresh_worker.wait()
            self.refresh_worker = None

    def closeEvent(self, event):
        # Clean up worker thread when closing
        if self.refresh_worker:
            self.refresh_worker.quit()
            self.refresh_worker.wait()
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
        # Clear existing content
        for i in reversed(range(frame.layout().count())):
            widget = frame.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Store the PR data in the frame
        frame.prs = prs  # Add this line to store the PR data
        
        is_empty = not prs
        if is_empty:
            label = QLabel("No PRs to display")
            frame.layout().addWidget(label)
            # Auto-collapse if empty
            if frame.is_expanded:
                frame.toggle_content()
            return
        
        # Auto-expand if not empty and was collapsed
        if not frame.is_expanded:
            frame.toggle_content()
        
        # Handle dict of PRs
        if isinstance(prs, dict):
            all_prs = []
            for user_prs in prs.values():
                if isinstance(user_prs, list):
                    all_prs.extend(user_prs)
                elif user_prs:
                    all_prs.append(user_prs)
            prs = all_prs
        elif not isinstance(prs, (list, tuple)):
            prs = [prs]
        
        # Filter PRs based on section
        if frame.title_label.text() == "Open PRs":
            prs = [pr for pr in prs if getattr(pr, 'state', '') == 'open' and not getattr(pr, 'merged_at', None)]
        elif frame.title_label.text() == "Recently Closed":
            prs = [pr for pr in prs if getattr(pr, 'state', '') == 'closed' or getattr(pr, 'merged_at', None)]
        
        # Check if section should be empty after filtering
        if not prs:
            label = QLabel("No PRs to display")
            frame.layout().addWidget(label)
            # Auto-collapse if empty after filtering
            if frame.is_expanded:
                frame.toggle_content()
            return
        
        # Add PR cards
        for pr in prs:
            if pr:
                card = create_pr_card(pr, self.settings)
                frame.layout().addWidget(card)

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
                
                # Compare refresh settings properly
                old_refresh = current_settings.get('refresh', {})
                new_refresh = settings.get('refresh', {})
                if (old_refresh.get('value') != new_refresh.get('value') or 
                    old_refresh.get('unit') != new_refresh.get('unit')):
                    print("\nDebug - Refresh settings changed:")
                    print(f"  Old: {old_refresh.get('value')} {old_refresh.get('unit')}")
                    print(f"  New: {new_refresh.get('value')} {new_refresh.get('unit')}")
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


def open_ui(open_prs_by_user, prs_awaiting_review_by_user,
            prs_that_need_attention_by_user, user_recently_closed_prs_by_user):
    app = QApplication([])
    app.setStyle('Fusion')
    
    window = PRWatcherUI()
    settings = load_settings()
    window.settings = settings  # Store settings in window
    window.consecutive_failures = 0  # Track failures for backoff
    window.max_backoff = 5  # Maximum backoff in seconds
    
    # Create GitHubPRs instance
    github_token = get_github_api_key()
    cache_duration = settings.get('cache_duration', 1)
    github_prs = GitHubPRs(
        github_token,
        recency_threshold=timedelta(days=1),
        cache_dir=".cache",
        cache_ttl=timedelta(hours=cache_duration)
    )
    window.github_prs = github_prs  # Store instance in window
    
    # Update initial data
    window.update_pr_lists(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user
    )
    
    # Set up refresh callback
    def refresh_callback():
        try:
            if window.consecutive_failures > 0:
                backoff = min(2 ** (window.consecutive_failures - 1), window.max_backoff)
                print(f"\nDebug - Backing off for {backoff} seconds due to previous failures")
                time.sleep(backoff)
            
            print("\nDebug - Fetching fresh PR data...")
            new_data = window.github_prs.get_pr_data(window.settings.get('users', []), force_refresh=True)
            if new_data is not None:
                window.update_pr_lists(*new_data)
                window.consecutive_failures = 0
            else:
                print("Debug - Refresh failed, keeping existing data")
                window.consecutive_failures += 1
            
        except Exception as e:
            window.consecutive_failures += 1
            print(f"Error refreshing data: {str(e)}")
            print(f"Consecutive failures: {window.consecutive_failures}")
        finally:
            window.loading_overlay.hide()
    
    window.set_refresh_callback(refresh_callback)
    
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