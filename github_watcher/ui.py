from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy
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
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        # Header container
        header_container = QFrame()
        header_container.setFixedHeight(30)  # Fixed height for header
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
        
        # Content container
        self.content_container = QFrame()
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.content_container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 5, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.main_layout.addWidget(self.content_container)
        
        # Make header clickable
        header_container.mousePressEvent = self.toggle_content
        header_container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Start collapsed
        self.is_expanded = True
        self.toggle_content()  # This will collapse it initially
    
    def toggle_content(self, event=None):
        self.is_expanded = not self.is_expanded
        self.content_container.setVisible(self.is_expanded)
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
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card.setStyleSheet("""
        QFrame#prCard {
            background-color: #2d2d2d;
            border-radius: 6px;
            padding: 10px;
            margin: 3px 0;
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
        
        # Initialize tracking for PRs with empty sets
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
        # First time initialization of tracking sets
        if not self.previously_closed_prs and isinstance(user_recently_closed_prs_by_user, dict):
            # Initialize with existing closed PRs to prevent "new PR" notifications for reopened PRs
            for prs in user_recently_closed_prs_by_user.values():
                for pr in prs:
                    pr_num = getattr(pr, 'number', None)
                    if pr_num:
                        self.previously_closed_prs.add(pr_num)
        
        # Get current open PRs
        current_open_prs = set()
        current_closed_prs = set()
        
        # Process open PRs and store PR objects for later reference
        pr_objects = {}  # Store PR objects by number for easy lookup
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
                        pr_objects[pr_num] = pr  # Also store closed PRs
        
        # Find PRs that were open but are no longer open
        disappeared_from_open = self.previously_open_prs - current_open_prs
        
        # Find newly closed PRs (was in open, now in closed)
        newly_closed = disappeared_from_open & current_closed_prs
        
        # Find new PRs (in open, wasn't before, and wasn't closed)
        new_prs = current_open_prs - self.previously_open_prs - self.previously_closed_prs
        
        # Find reopened PRs (was in closed, now in open)
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
        print(f"Notified PRs: {self.notified_prs}")
        
        # Reset notifications for state changes
        self.notified_prs -= reopened_prs  # Reset for reopened PRs
        self.notified_prs -= disappeared_from_open  # Reset for closed PRs
        
        # Send notifications for changes
        if newly_closed:  # Removed the notified_prs check for closed PRs
            closed_details = []
            for pr_num in newly_closed:
                if pr := pr_objects.get(pr_num):
                    repo = f"{pr.repo_owner}/{pr.repo_name}"
                    author = pr.user.login if pr.user else "Unknown"
                    closed_details.append(f"#{pr_num} - {pr.title}\nRepo: {repo}\nAuthor: {author}")
            
            if closed_details:
                notify(NOTIFIER_APP, "PRs Closed", 
                      "Recently closed PRs:\n" + "\n\n".join(closed_details))
                self.notified_prs.update(newly_closed)
        
        if new_prs - self.notified_prs:
            new_details = []
            for pr_num in new_prs - self.notified_prs:
                if pr := pr_objects.get(pr_num):
                    repo = f"{pr.repo_owner}/{pr.repo_name}"
                    author = pr.user.login if pr.user else "Unknown"
                    new_details.append(f"#{pr_num} - {pr.title}\nRepo: {repo}\nAuthor: {author}")
            
            if new_details:
                notify(NOTIFIER_APP, "New PRs", 
                      "New PRs opened:\n" + "\n\n".join(new_details))
                self.notified_prs.update(new_prs)
        
        if reopened_prs:
            reopen_details = []
            for pr_num in reopened_prs:
                if pr := pr_objects.get(pr_num):
                    repo = f"{pr.repo_owner}/{pr.repo_name}"
                    author = pr.user.login if pr.user else "Unknown"
                    reopen_details.append(f"#{pr_num} - {pr.title}\nRepo: {repo}\nAuthor: {author}")
            
            if reopen_details:
                notify(NOTIFIER_APP, "PRs Reopened", 
                      "PRs reopened:\n" + "\n\n".join(reopen_details))
                self.notified_prs.update(reopened_prs)
        
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