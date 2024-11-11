from PyQt6.QtWidgets import (
    QFrame, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QWidget, 
    QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from .theme import Colors, Styles

class SectionFrame(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.title = title
        self.prs = {}
        self.spinner_label = None
        self.spinner_timer = None
        self.is_loading = False
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None
        self.is_expanded = True

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

        # Left side of header (title, toggle, and spinner)
        left_header = QWidget()
        left_header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.left_layout = QHBoxLayout(left_header)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(5)

        # Title label with count
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        self.left_layout.addWidget(self.title_label)

        # Count label
        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(
            """
            QLabel {
                color: #8b949e;
                font-size: 12px;
                padding-left: 5px;
            }
        """
        )
        self.left_layout.addWidget(self.count_label)

        # Create spinner
        self.create_spinner()

        # Toggle button
        self.toggle_button = QLabel("▼")
        self.toggle_button.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                padding: 0px 5px;
                font-size: 12px;
            }
            QLabel:hover {
                color: #cccccc;
            }
        """
        )
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.mousePressEvent = lambda _: self.toggle_content()
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.left_layout.addWidget(self.toggle_button)
        self.left_layout.addStretch()

        header_layout.addWidget(left_header)
        self.main_layout.addWidget(header_container)
        print(f"Debug - Header created for {self.title}")

    def create_scroll_area(self):
        """Create or recreate scroll area and content widget"""
        print(f"\nDebug - Creating scroll area for {self.title}")
        try:
            # Clean up old widgets if they exist
            if hasattr(self, "scroll_area"):
                try:
                    self.scroll_area.deleteLater()
                except:
                    pass
            if hasattr(self, "content_widget"):
                try:
                    self.content_widget.deleteLater()
                except:
                    pass

            # Create new widgets
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setStyleSheet(
                """
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
            """
            )

            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(5)

            self.scroll_area.setWidget(self.content_widget)
            self.main_layout.addWidget(self.scroll_area)
            print(f"Debug - Scroll area created for {self.title}")

        except Exception as e:
            print(f"Error creating scroll area: {e}")

    def toggle_content(self):
        """Toggle the visibility of the content"""
        print(f"\nDebug - Toggling content for {self.title}")
        if not self.scroll_area:
            return

        self.is_expanded = not self.is_expanded
        self.scroll_area.setVisible(self.is_expanded)
        self.toggle_button.setText("▼" if self.is_expanded else "▶")
        print(f"Debug - Content toggled: {'expanded' if self.is_expanded else 'collapsed'}")

    def create_spinner(self):
        """Create spinner label and timer"""
        print(f"\nDebug - Creating spinner for {self.title}")
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
            self.spinner_label.setStyleSheet(
                """
                QLabel {
                    color: #0d6efd;
                    font-size: 14px;
                    padding: 0 5px;
                }
            """
            )
            self.spinner_label.hide()

            # Add to layout if we have one
            if hasattr(self, "left_layout"):
                self.left_layout.addWidget(self.spinner_label)

            # Create new timer
            self.spinner_timer = QTimer(self)
            self.spinner_timer.timeout.connect(self.rotate_spinner)
            self.spinner_timer.setInterval(50)
            self.spinner_rotation = 0
            print(f"Debug - Spinner created for {self.title}")

        except Exception as e:
            print(f"Warning: Error creating spinner: {e}")
            self.spinner_label = None
            self.spinner_timer = None

    def rotate_spinner(self):
        """Rotate the spinner icon"""
        if not hasattr(self, "spinner_rotation"):
            self.spinner_rotation = 0

        self.spinner_rotation = (self.spinner_rotation + 30) % 360
        if self.spinner_label and self.spinner_label.parent():
            self.spinner_label.setStyleSheet(
                f"""
                QLabel {{
                    color: #0d6efd;
                    font-size: 14px;
                    padding: 0 5px;
                    transform: rotate({self.spinner_rotation}deg);
                }}
            """
            )

    def update_count(self, count):
        """Update the count display"""
        print(f"\nDebug - Updating count for {self.title}: {count}")
        self.count_label.setText(f"({count})")

    def start_loading(self):
        """Start loading animation"""
        if self.is_loading:
            return

        print(f"\nDebug - Starting loading animation for {self.title}")
        self.is_loading = True
        try:
            if not self.spinner_label or not self.spinner_label.parent():
                self.create_spinner()

            if self.spinner_label and self.spinner_label.parent():
                self.spinner_label.show()
                if self.spinner_timer:
                    self.spinner_timer.start()
        except Exception as e:
            print(f"Warning: Error starting loading animation: {e}")

    def stop_loading(self):
        """Stop loading animation"""
        print(f"\nDebug - Stopping loading animation for {self.title}")
        self.is_loading = False
        try:
            if self.spinner_timer and self.spinner_timer.isActive():
                self.spinner_timer.stop()
            if self.spinner_label and self.spinner_label.parent():
                self.spinner_label.hide()
        except Exception as e:
            print(f"Warning: Error stopping loading animation: {e}") 