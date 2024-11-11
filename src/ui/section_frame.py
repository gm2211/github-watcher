import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import Colors, Styles


class SectionFrame(QFrame):
    def __init__(self, title, state, parent=None):
        super().__init__(parent)
        self.title = title
        self.state = state
        self.setObjectName(Styles.SECTION_FRAME_CSS_CLASS)
        # Allow vertical expansion but prefer minimum size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.prs = {}
        self.is_loading = False
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None

        # Load saved state
        print(f"\nDebug - Loading state for section {title}")
        key = f"section_{title}_expanded"
        self.is_expanded = self.state.settings.get(key, True)
        print(f"Debug - Loaded state: {key}={self.is_expanded}")

        # Use theme styles
        self.setStyleSheet(Styles.SECTION_FRAME)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # Create UI elements
        self.create_header()
        self.create_scroll_area()

        # Apply saved state
        if not self.is_expanded:
            self.setMaximumHeight(
                self.header_container.height() + 20
            )  # Header height + margins
            if self.scroll_area:
                self.scroll_area.hide()
            if self.toggle_button:
                self.toggle_button.setText("▶")
            print(f"Debug - Applied collapsed state to {title}")

    def create_header(self):
        """Create header section"""
        print(f"\nDebug - Creating header for {self.title}")
        # Make the entire header clickable
        self.header_container = QFrame()  # Store reference for height calculations
        self.header_container.setFixedHeight(30)
        self.header_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.header_container.setStyleSheet(
            """
            QFrame {
                background: transparent;
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """
        )
        self.header_container.mousePressEvent = lambda _: self.toggle_content()
        self.header_container.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout = QHBoxLayout(self.header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        # Left side of header (title and toggle)
        left_header = QWidget()
        left_header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        left_header.setStyleSheet("background: transparent;")
        self.left_layout = QHBoxLayout(left_header)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(5)

        # Title label with count
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        self.left_layout.addWidget(self.title_label)

        # Count label
        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.left_layout.addWidget(self.count_label)

        # Toggle button
        self.toggle_button = QLabel("▼" if self.is_expanded else "▶")
        self.toggle_button.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                padding: 0px 5px;
                font-size: 12px;
            }}
        """
        )
        self.toggle_button.setFixedSize(20, 20)
        self.left_layout.addWidget(self.toggle_button)
        self.left_layout.addStretch()

        header_layout.addWidget(left_header)
        self.main_layout.addWidget(self.header_container)

    def create_scroll_area(self):
        """Create or recreate scroll area and content widget"""
        print(f"\nDebug - Creating scroll area for {self.title}")
        try:
            # Clean up old widgets if they exist
            if hasattr(self, "scroll_area") and self.scroll_area is not None:
                self.scroll_area.deleteLater()
            if hasattr(self, "content_widget") and self.content_widget is not None:
                self.content_widget.deleteLater()

            # Create new widgets
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setStyleSheet(Styles.SCROLL_AREA)
            self.scroll_area.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )

            # Create content widget and layout
            self.content_widget = QWidget()
            self.content_widget.setStyleSheet("background: transparent;")
            self.content_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(5)

            # Set the widget in the scroll area
            self.scroll_area.setWidget(self.content_widget)
            self.main_layout.addWidget(self.scroll_area)

            print(f"Debug - Scroll area created for {self.title}")

        except Exception as e:
            print(f"Error creating scroll area: {e}")
            traceback.print_exc()

    def toggle_content(self):
        """Toggle the visibility of the content"""
        if not self.scroll_area:
            return

        print(f"\nDebug - Toggling section {self.title}")
        print(f"Debug - Current state: expanded={self.is_expanded}")

        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.scroll_area.show()
        else:
            self.setMaximumHeight(
                self.header_container.height() + 20
            )  # Header height + margins
            self.scroll_area.hide()

        self.toggle_button.setText("▼" if self.is_expanded else "▶")

        print(f"Debug - New state: expanded={self.is_expanded}")

        # Save state
        key = f"section_{self.title}_expanded"
        self.state.settings[key] = self.is_expanded

        try:
            self.state.save()
            print(f"Debug - Section state saved for {self.title}")
        except Exception as e:
            print(f"Error saving state: {e}")
            traceback.print_exc()

    def update_count(self, count):
        """Update the count display"""
        self.count_label.setText(f"({count})")

    def start_loading(self):
        """Start loading state"""
        self.is_loading = True

    def stop_loading(self):
        """Stop loading state"""
        self.is_loading = False
