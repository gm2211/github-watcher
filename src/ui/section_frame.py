from PyQt6.QtWidgets import (
    QFrame, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QWidget, 
    QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .theme import Colors, Styles
import traceback

class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.title = title
        self.prs = {}
        self.is_loading = False
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None
        self.is_expanded = True

        # Use theme styles
        self.setStyleSheet(Styles.SECTION_FRAME)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # Create UI elements
        self.create_header()
        self.create_scroll_area()

    def create_header(self):
        """Create header section"""
        print(f"\nDebug - Creating header for {self.title}")
        header_container = QFrame()
        header_container.setFixedHeight(30)
        header_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_container)
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
        self.toggle_button = QLabel("▼")
        self.toggle_button.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                padding: 0px 5px;
                font-size: 12px;
            }}
            QLabel:hover {{
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.mousePressEvent = lambda _: self.toggle_content()
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.left_layout.addWidget(self.toggle_button)
        self.left_layout.addStretch()

        header_layout.addWidget(left_header)
        self.main_layout.addWidget(header_container)

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
            self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

            # Create content widget and layout
            self.content_widget = QWidget()
            self.content_widget.setStyleSheet("background: transparent;")
            self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
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

        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self.toggle_button.setText("▼" if self.is_expanded else "▶")

    def update_count(self, count):
        """Update the count display"""
        self.count_label.setText(f"({count})")

    def start_loading(self):
        """Start loading state"""
        self.is_loading = True

    def stop_loading(self):
        """Stop loading state"""
        self.is_loading = False