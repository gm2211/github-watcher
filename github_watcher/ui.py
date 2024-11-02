from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
import webbrowser
from datetime import datetime, timezone
import platform
import os
from notifications import notify, NOTIFIER_APP


class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.setStyleSheet("""
            QFrame#sectionFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)  # Reduced spacing between elements
        
        # Title container to ensure it stays at top
        title_container = QFrame()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        
        # Title label
        title_label = QLabel(title)
        title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        # Add title container at the top
        layout.addWidget(title_container, 0)  # 0 stretch factor keeps it at minimum size
        
        # Add content container that will expand
        content_container = QFrame()
        content_container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_container, 1)  # 1 stretch factor allows it to expand
        
        # Store references
        self.title_label = title_label
        self.content_layout = content_layout
        
    def layout(self):
        # Override to return the content layout instead of the main layout
        return self.content_layout


def create_badge(text, bg_color, fg_color="white", parent=None):
    badge = QFrame(parent)
    badge.setStyleSheet(f"""
        QFrame {{
            background-color: {bg_color};
            border-radius: 12px;
            padding: 2px 6px;
            min-width: 45px;
            max-width: 45px;
            min-height: 22px;
            max-height: 22px;
        }}
    """)
    
    layout = QHBoxLayout(badge)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(0)
    
    label = QLabel(text)
    label.setStyleSheet(f"""
        color: {fg_color};
        font-size: 10px;
        padding: 0;
    """)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    return badge


def create_pr_card(pr_data, parent=None):
    if isinstance(pr_data, list):
        if not pr_data:
            label = QLabel("No PRs to display")
            return label
        pr_data = pr_data[0]
    
    card = QFrame(parent)
    card.setObjectName("prCard")
    card.setStyleSheet("""
        QFrame#prCard {
            background-color: #2d2d2d;
            border-radius: 6px;
            padding: 10px;
            margin: 3px 0;
        }
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(8)
    
    # Header section
    header = QHBoxLayout()
    
    # Title with PR number
    title_text = f"{getattr(pr_data, 'title', 'Untitled')} (#{getattr(pr_data, 'number', '?')})"
    title = QLabel(title_text)
    title.setFont(QFont("", 13, QFont.Weight.Bold))
    title.setStyleSheet("color: #58a6ff; text-decoration: underline;")
    title.setCursor(Qt.CursorShape.PointingHandCursor)
    if url := getattr(pr_data, 'html_url', None):
        title.mousePressEvent = lambda _: webbrowser.open(url)
    header.addWidget(title)
    
    # Badges
    badges_layout = QHBoxLayout()
    badges_layout.setSpacing(4)
    
    if getattr(pr_data, 'draft', False):
        draft_badge = create_badge("DRAFT", "#6c757d")
        badges_layout.addWidget(draft_badge)
    
    if getattr(pr_data, 'merged_at', None):
        status_badge = create_badge("MERGED", "#6f42c1")
    elif getattr(pr_data, 'state', '') == 'closed':
        status_badge = create_badge("CLOSED", "#dc3545")
    else:
        status_badge = create_badge("OPEN", "#28a745")
    badges_layout.addWidget(status_badge)
    
    header.addLayout(badges_layout)
    layout.addLayout(header)
    
    # Info section
    info_layout = QHBoxLayout()
    
    # Left info
    left_info = QVBoxLayout()
    
    # Author info
    user = getattr(pr_data, 'user', None)
    if user and hasattr(user, 'login'):
        author_text = f"Author: {user.login}"
        author_label = QLabel(author_text)
        author_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        left_info.addWidget(author_label)
    
    # Comments info
    timeline = getattr(pr_data, 'timeline', [])
    if timeline:
        comments = [event for event in timeline if 'comments' in getattr(event, 'url', '')]
        comments_count = len(comments)
        if comments_count > 0:
            comments_text = f"💬 {comments_count} comment{'s' if comments_count != 1 else ''}"
            comments_label = QLabel(comments_text)
            comments_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            left_info.addWidget(comments_label)
            
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
                    last_comment_label.setStyleSheet("color: #8b949e; font-size: 11px;")
                    left_info.addWidget(last_comment_label)
    
    info_layout.addLayout(left_info)
    
    # Right info
    right_info = QVBoxLayout()
    right_info.setAlignment(Qt.AlignmentFlag.AlignRight)
    
    if updated := getattr(pr_data, 'updated_at', None):
        try:
            if isinstance(updated, str):
                updated_date = datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            else:
                updated_date = updated
            
            now = datetime.now(timezone.utc)
            time_diff = now - updated_date
            time_text = f"Updated {format_time_diff(time_diff)}"
            
            updated_label = QLabel(time_text)
            updated_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            right_info.addWidget(updated_label)
        except (ValueError, TypeError) as e:
            print(f"Error parsing update date: {e}")
    
    info_layout.addLayout(right_info)
    layout.addLayout(info_layout)
    
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
        test_notif_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        buttons_layout.addWidget(test_notif_btn)
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                color: white;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        buttons_layout.addWidget(refresh_btn)
        
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
        self.auto_refresh_timer.start(10000)  # 10 seconds
        
        # Initialize tracking for PRs
        self.previously_open_prs = set()
        self.previously_closed_prs = set()
        self.notified_prs = set()
        
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

    def show_test_notification(self):
        notify(NOTIFIER_APP, "GitHub PR Watcher", "Test notification - System is working!")

    def refresh_data(self):
        if hasattr(self, 'refresh_callback'):
            print("\nDebug - Starting refresh...")
            self.refresh_callback()
            print("Debug - Refresh completed")

    def set_refresh_callback(self, callback):
        self.refresh_callback = callback

    def update_pr_lists(self, open_prs_by_user, prs_awaiting_review_by_user,
                       prs_that_need_attention_by_user, user_recently_closed_prs_by_user):
        self._update_section(self.needs_review_frame, prs_awaiting_review_by_user)
        self._update_section(self.changes_requested_frame, prs_that_need_attention_by_user)
        self._update_section(self.open_prs_frame, open_prs_by_user)
        self._update_section(self.recently_closed_frame, user_recently_closed_prs_by_user)

    def _update_section(self, frame, prs):
        # Clear existing content
        for i in reversed(range(frame.layout().count())):
            widget = frame.layout().itemAt(i).widget()
            if widget != frame.title_label:
                widget.deleteLater()
        
        if not prs:
            label = QLabel("No PRs to display")
            frame.layout().addWidget(label)
            return
        
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
        
        # Add PR cards
        for pr in prs:
            if pr:
                card = create_pr_card(pr)
                frame.layout().addWidget(card)


def open_ui(open_prs_by_user, prs_awaiting_review_by_user,
            prs_that_need_attention_by_user, user_recently_closed_prs_by_user):
    app = QApplication([])
    app.setStyle('Fusion')  # Use Fusion style for consistent cross-platform look
    
    window = PRWatcherUI()
    
    # Update initial data
    window.update_pr_lists(
        open_prs_by_user,
        prs_awaiting_review_by_user,
        prs_that_need_attention_by_user,
        user_recently_closed_prs_by_user
    )
    
    # Set up refresh callback
    def refresh_callback():
        from utils import get_pr_data, read_users_from_file
        
        users = read_users_from_file()
        if not users:
            return
        
        try:
            print("\nDebug - Fetching fresh PR data...")
            new_data = get_pr_data(users)
            window.update_pr_lists(*new_data)
        except Exception as e:
            error_msg = f"Error refreshing data: {str(e)}"
            print(f"Error: {error_msg}")
            notify(NOTIFIER_APP, "Error", error_msg)
    
    window.set_refresh_callback(refresh_callback)
    window.show()
    
    return app.exec()