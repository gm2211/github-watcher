from typing import Optional

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

from github_pr_watcher.ui.themes import Colors, Styles
from github_pr_watcher.ui.ui_state import SectionName, UIState


class SectionFrame(QFrame):
    def __init__(
        self, name: SectionName, ui_state: UIState, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.name: SectionName = name
        self.ui_state: UIState = ui_state

        self._setup_ui()
        self._apply_state()

    def _setup_ui(self) -> None:
        """Setup the UI components"""
        self.setObjectName(Styles.SECTION_FRAME_CSS_CLASS)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(Styles.SECTION_FRAME)

        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # Create UI elements
        self._create_header()
        self._create_content_area()

    def _create_header(self) -> None:
        """Create the header section"""
        self.header = QFrame()
        self.header.setFixedHeight(30)
        self.header.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.header.setStyleSheet(
            f"""
            QFrame {{
                background: transparent;
            }}
            QFrame:hover {{
                background: {Colors.HOVER_OVERLAY};
            }}
            """
        )
        self.header.mousePressEvent = lambda _: self.toggle_content()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        # Title and count
        self.title_label = QLabel(self.name.value)
        self.title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

        # Toggle button
        self.toggle_button = QLabel("▼" if self.is_expanded() else "▶")
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

        # Add to layout
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.count_label)
        header_layout.addWidget(self.toggle_button)
        header_layout.addStretch()

        self.main_layout.addWidget(self.header)

    def _create_content_area(self) -> None:
        """Create the scrollable content area"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(Styles.SCROLL_AREA)
        self.scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    def _apply_state(self) -> None:
        """Apply the current state to the UI"""
        if not self.is_expanded():
            self.setMaximumHeight(self.header.height() + 20)
            self.scroll_area.hide()
            self.toggle_button.setText("▶")
        else:
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self.scroll_area.show()
            self.toggle_button.setText("▼")

    def toggle_content(self) -> None:
        """Toggle the visibility of the content"""
        self.ui_state.set_section_expanded(self.name, not self.is_expanded())
        self._apply_state()

    def update_count(self, count: int) -> None:
        """Update the count display"""
        self.count_label.setText(f"({count})")

    def is_expanded(self):
        return self.ui_state.get_section_expanded(self.name)
        pass
