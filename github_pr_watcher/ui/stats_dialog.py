import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QComboBox,
    QHBoxLayout,
    QWidget,
    QHeaderView,
    QTabWidget,
    QProgressBar,
    QFrame,
    QSizePolicy,
    QCheckBox,
)

from github_pr_watcher.settings import Settings
from github_pr_watcher.ui.themes import Colors, Styles
from github_pr_watcher.utils import ftoi

SECONDS_PER_DAY = 86400

# Configure matplotlib
plt.style.use('dark_background')
plt.rcParams.update({
    'figure.dpi': 100,
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.bottom': False,
    'axes.spines.left': False,
    'figure.facecolor': Colors.BG_DARK,
    'axes.facecolor': Colors.BG_DARK,
})


class StyledFrame(QFrame):
    """A styled frame with rounded corners and a subtle border"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARKER};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 16px;
            }}
        """)


@dataclass
class ColumnData:
    """Data for a table column"""
    value: int | float
    rank: float
    reverse: bool = False  # True if lower values are better (like PR age)


@dataclass
class UserStats:
    """Statistics for a single user"""
    user: str = ""
    created: int = 0
    merged: int = 0
    commented: int = 0
    active: int = 0
    total_lines_added: int = 0
    total_commits: int = 0
    total_prs: int = 0
    total_merged_prs: int = 0
    total_pr_age: timedelta = field(default_factory=lambda: timedelta())
    total_time_to_merge: timedelta = field(default_factory=lambda: timedelta())
    total_time_since_comment: timedelta = field(default_factory=lambda: timedelta())

    @property
    def avg_lines_added(self) -> int:
        return ftoi(self.total_lines_added / max(1, self.total_prs))

    @property
    def avg_pr_age_days(self) -> int:
        return ftoi(self.total_pr_age.total_seconds() / (max(1, self.total_prs) * SECONDS_PER_DAY))

    @property
    def avg_time_to_merge_days(self) -> int:
        return ftoi(self.total_time_to_merge.total_seconds() / (max(1, self.total_merged_prs) * SECONDS_PER_DAY))

    @property
    def avg_time_since_comment_days(self) -> int:
        return ftoi(self.total_time_since_comment.total_seconds() / (max(1, self.total_prs) * SECONDS_PER_DAY))

    @property
    def avg_commits(self) -> int:
        return ftoi(self.total_commits / max(1, self.total_prs))


def _get_gradient_color(rank: float, reverse: bool = False) -> str:
    colors = [
        "#A3D2DA",  # Light blue-gray
        "#92C3CC",
        "#81B4BE",
        "#70A5B0",
        "#5F96A2",
        "#4E8794",
        "#3D7886",
        "#2C6978",
        "#1B5A7A",
        "#0A4B6C",  # Dark whale blue
    ]

    if reverse:
        colors = list(reversed(colors))

    # Convert rank to index (0-9)
    index = min(len(colors) - 1, max(0, int(rank * 10)))
    return colors[index]


def _get_rank(value: float, values: List[float]) -> float:
    """Get the rank (0-1) of a value in a sorted list of values
    If all values are the same, they all get rank 0 (best)
    """
    if not values:
        return 0

    # If all values are the same, return 0 (best rank)
    if len(set(values)) == 1:
        return 0

    # Sort values in ascending order
    sorted_values = sorted(values)

    # Find position of value (or where it would be inserted)
    for i, v in enumerate(sorted_values):
        if value <= v:
            return i / max(1, len(sorted_values) - 1)

    # If we get here, the value is larger than all others
    return 1.0


class ColoredTableItem(QTableWidgetItem):
    def __init__(self, text: str, background_color: str, text_color: str = Colors.TEXT_PRIMARY):
        super().__init__(text)
        self._background_color = background_color
        self._text_color = text_color
        self.setBackground(QColor(background_color))
        self.setForeground(QColor(text_color))

    def clone(self):
        return ColoredTableItem(self.text(), self._background_color, self._text_color)


def _get_text_color(background_color: str) -> str:
    """Get appropriate text color (black or white) based on background brightness"""
    # Remove '#' and convert to RGB
    r = int(background_color[1:3], 16)
    g = int(background_color[3:5], 16)
    b = int(background_color[5:7], 16)
    
    # Calculate perceived brightness using the formula: (R * 299 + G * 587 + B * 114) / 1000
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    
    # Use black text for light backgrounds, white text for dark backgrounds
    return Colors.TEXT_PRIMARY if brightness < 128 else "#000000"


class StatsDialog(QDialog):
    def __init__(self, ui_state, settings: Settings, parent=None):
        super().__init__(parent)
        self.ui_state = ui_state
        self.settings = settings
        self.setWindowTitle("User Statistics")
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_DARK};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {Colors.BG_DARKER};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 20px;
                margin-right: 4px;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.BG_LIGHT};
                border-bottom: 2px solid {Colors.INFO};
            }}
        """)
        self.setMinimumSize(1200, 800)

        # Create main layout with margins for better spacing
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Create loading indicator
        self.loading = QProgressBar()
        self.loading.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 8px;
                text-align: center;
                background-color: {Colors.BG_DARKER};
                height: 24px;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.INFO};
                border-radius: 6px;
            }}
        """)
        self.loading.setTextVisible(True)
        self.loading.setFormat("Initializing visualization...")
        layout.addWidget(self.loading)

        # Create period selector and toggle in a styled frame
        controls_frame = StyledFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Period selector
        period_label = QLabel("Time Period:")
        period_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
        """)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last Week", "Last Month", "Last 3 Months"])
        self.period_combo.setStyleSheet(Styles.COMBO_BOX)
        self.period_combo.currentTextChanged.connect(self.update_stats)

        # Bot comments toggle
        self.include_bots_toggle = QCheckBox("Include Bot Comments")
        self.include_bots_toggle.setChecked(True)
        self.include_bots_toggle.setStyleSheet(Styles.CHECKBOX)
        self.include_bots_toggle.stateChanged.connect(self.update_stats)

        controls_layout.addWidget(period_label)
        controls_layout.addWidget(self.period_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.include_bots_toggle)

        layout.addWidget(controls_frame)

        # Initialize matplotlib components right away with dynamic sizing
        self.figure = Figure()  # Remove fixed figsize
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_DARKER};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 8px;
                min-height: 600px;  /* Ensure minimum height */
            }}
        """)

        # Set size policy to make canvas expand
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create and add summary tab
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.setContentsMargins(0, 16, 0, 0)
        self.table = self._create_summary_table()
        summary_layout.addWidget(self.table)
        self.tab_widget.addTab(summary_tab, "Summary")

        # Create and add heatmap tab
        heatmap_tab = QWidget()
        self.heatmap_layout = QVBoxLayout(heatmap_tab)
        self.heatmap_layout.setContentsMargins(0, 16, 0, 0)
        self.heatmap_layout.addWidget(self.canvas)
        self.tab_widget.addTab(heatmap_tab, "Commenter Heatmap")

        layout.addWidget(self.tab_widget)

        # Hide loading initially
        self.loading.hide()

        # Schedule initial update after a short delay
        QTimer.singleShot(100, self._delayed_init)

    def _delayed_init(self):
        """Initialize stats after UI is shown"""
        self.loading.show()
        QTimer.singleShot(0, self._do_init)

    def _do_init(self):
        """Actually perform initialization"""
        try:
            self.update_stats()
        finally:
            self.loading.hide()

    def _create_summary_table(self) -> QTableWidget:
        """Create the summary statistics table"""
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 6px;
                gridline-color: {Colors.BORDER_DEFAULT};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_DARKER};
                color: {Colors.TEXT_PRIMARY};
                padding: 5px;
                border: 1px solid {Colors.BORDER_DEFAULT};
            }}
        """)

        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(True)

        # Set up columns
        self.columns = [
            ("User", str),
            ("Active PRs", int),
            ("PRs Merged", float),
            ("PRs Commented", float),
            ("Avg Lines Added", int),
            ("Avg PR Age (days)", float),
            ("Avg TTM (days)", float),
            ("Avg TSLC (days)", float),
            ("Avg Commits", float)
        ]
        table.setColumnCount(len(self.columns))
        table.setHorizontalHeaderLabels([col[0] for col in self.columns])

        # Set column stretch behavior
        header = table.horizontalHeader()
        header.setStyleSheet(f"background-color: {Colors.BG_DARKER};")
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # All columns get equal stretch
        for i in range(len(self.columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        return table

    def _calculate_user_stats(self, selected_period_days: int) -> Dict[str, UserStats]:
        """Calculate user statistics - only for configured users"""
        cutoff_date = datetime.now().astimezone() - timedelta(days=selected_period_days)
        stats_by_user: Dict[str, UserStats] = {}

        # Initialize stats for all configured users
        for user in sorted(set(self.settings.users)):
            stats_by_user[user] = UserStats()

        now = datetime.now().astimezone()

        # Process each section's PRs
        processed_prs = set()  # Track processed PRs to avoid duplicates
        for section_data in self.ui_state.data_by_section.values():
            if not section_data:
                continue

            for prs in section_data.prs_by_author.values():
                for pr in prs:
                    # Skip if we've already processed this PR
                    if pr.id in processed_prs:
                        continue
                    processed_prs.add(pr.id)

                    pr_author = pr.user.login
                    # Only process if author is in configured users
                    if pr_author in stats_by_user:
                        user_stats = stats_by_user[pr_author]

                        # Count created PRs
                        if pr.created_at >= cutoff_date:
                            user_stats.created += 1
                            user_stats.total_prs += 1
                            user_stats.total_lines_added += (pr.additions or 0)

                            # Calculate PR age
                            if pr.merged_at:
                                pr_age = pr.merged_at - pr.created_at
                            else:
                                pr_age = now - pr.created_at
                            user_stats.total_pr_age += pr_age

                            # Calculate time since last comment if available
                            if pr.last_comment_time:
                                time_since_comment = now - pr.last_comment_time
                                user_stats.total_time_since_comment += time_since_comment

                        # Count merged PRs and calculate time to merge
                        if pr.merged and pr.merged_at and pr.merged_at >= cutoff_date:
                            user_stats.merged += 1
                            user_stats.total_merged_prs += 1
                            merge_time = pr.merged_at - pr.created_at
                            user_stats.total_time_to_merge += merge_time

                        # Count active PRs
                        if pr.state.lower() == "open" and not pr.archived:
                            user_stats.active += 1

                        user_stats.total_commits += (pr.commit_count or 0)

                    # Count comments for all configured users
                    for commenter, count in (pr.comment_count_by_author or {}).items():
                        if commenter in stats_by_user and commenter != pr_author:
                            if pr.last_comment_time and pr.last_comment_time >= cutoff_date:
                                stats_by_user[commenter].commented += 1

        return stats_by_user

    def _calculate_comment_heatmap(self, selected_period_days: int) -> Tuple[np.ndarray, List[str], List[str]]:
        """Calculate comment frequency between authors and commenters"""
        cutoff_date = datetime.now().astimezone() - timedelta(days=selected_period_days)
        comment_counts = {}  # author -> commenter -> count
        all_commenters = set()  # Track all users who have commented
        include_bots = self.include_bots_toggle.isChecked()

        # First pass: collect all commenters and initialize counts for configured users
        for user in self.settings.users:
            comment_counts[user] = {}

        # Process PRs to build comment counts
        for section_data in self.ui_state.data_by_section.values():
            if not section_data:
                continue

            for user_prs in section_data.prs_by_author.values():
                for pr in user_prs:
                    # Only process PRs from configured users
                    if pr.user.login not in self.settings.users:
                        continue

                    if pr.created_at < cutoff_date:
                        continue

                    # Count comments
                    for commenter, count in (pr.comment_count_by_author or {}).items():
                        # Skip bot comments if toggle is off
                        if not include_bots and commenter.endswith("[bot]"):
                            continue

                        if commenter != pr.user.login:  # Don't count self-comments
                            all_commenters.add(commenter)
                            comment_counts[pr.user.login][commenter] = (
                                    comment_counts[pr.user.login].get(commenter, 0) + count
                            )

        # Convert to numpy array for heatmap
        authors = sorted(self.settings.users)  # Only configured users as authors
        commenters = sorted(all_commenters)  # All commenters
        matrix = np.zeros((len(commenters), len(authors)))

        for i, author in enumerate(authors):
            for j, commenter in enumerate(commenters):
                if author != commenter:  # Skip self-comments
                    matrix[j, i] = comment_counts[author].get(commenter, 0)

        return matrix, authors, commenters

    def _update_heatmap(self, matrix: np.ndarray, authors: List[str], commenters: List[str]):
        """Update the heatmap visualization using seaborn"""
        import seaborn as sns
        self.figure.clear()

        # Create axis with dark theme
        ax = self.figure.add_subplot(111)

        # Handle empty data
        if len(authors) == 0 or len(commenters) == 0:
            ax.text(0.5, 0.5, 'No data available',
                    horizontalalignment='center',
                    verticalalignment='center',
                    color=Colors.TEXT_PRIMARY,
                    fontsize=14,
                    fontweight='bold')
            self.canvas.draw()
            return

        # Create custom colormap with blue gradients
        colors = [
            "#607d8b",  # Start with a muted blue-gray
            "#5a7788",
            "#547284",
            "#4f6c81",
            "#4a677d",
            "#45617a",
            "#415c76",
            "#3d5672",
            "#39506f",
            "#354b6b",
            "#324567",
            "#304063",
            "#2d3a5f",
            "#2b355a",
            "#292f56"  # End with a deep blue
        ]
        custom_cmap = sns.color_palette(colors, as_cmap=True)

        # Create heatmap with improved styling
        sns.heatmap(
            matrix,
            ax=ax,
            xticklabels=authors,
            yticklabels=commenters,
            cmap=custom_cmap,
            annot=True,
            fmt='g',
            cbar_kws={
                'label': 'Number of Comments',
                'orientation': 'horizontal',
                'pad': 0.2,
                'shrink': 0.8,
                'aspect': 40,
                'drawedges': False,
            },
            square=True,
            mask=matrix == 0,
            annot_kws={
                'size': 10,
                'weight': 'bold',
                'color': Colors.TEXT_PRIMARY,
            },
            cbar=True,
            linewidths=0.5,  # Add thin grid lines
            linecolor=Colors.BORDER_DEFAULT,  # Use theme border color
        )

        # Customize appearance
        ax.set_xlabel('Author', color=Colors.TEXT_PRIMARY, labelpad=15)
        ax.set_ylabel('Commenter', color=Colors.TEXT_PRIMARY, labelpad=15)

        # Style the ticks
        ax.tick_params(colors=Colors.TEXT_PRIMARY, which='both', length=0)
        plt.setp(ax.get_xticklabels(),
                 rotation=45,
                 ha='right',
                 rotation_mode='anchor',
                 fontsize=11)
        plt.setp(ax.get_yticklabels(),
                 rotation=0,
                 fontsize=11)

        # Add subtle grid
        ax.grid(False)

        # Adjust layout to prevent label cutoff
        self.figure.tight_layout()

        # Refresh canvas
        self.canvas.draw()

    def _get_period_days(self) -> int:
        period = self.period_combo.currentText()
        if period == "Last Week":
            return 7
        elif period == "Last Month":
            return 30
        else:  # Last 3 Months
            return 90

    def update_stats(self):
        selected_period_days = self._get_period_days()

        # Update summary table (only configured users)
        stats_by_user = self._calculate_user_stats(selected_period_days)

        # Clear the table first
        self.table.clearContents()
        self.table.setRowCount(0)

        # Sort users to ensure consistent ordering
        sorted_users = sorted(stats_by_user.keys())
        self.table.setRowCount(len(sorted_users))

        # Disable sorting while updating
        self.table.setSortingEnabled(False)

        try:
            # Get all values for ranking once
            all_stats = list(stats_by_user.values())

            # Update table row by row
            for row_idx, user in enumerate(sorted_users):
                user_stats = stats_by_user[user]

                # Create all items for this row
                row_items = []

                # User column (no coloring)
                user_item = ColoredTableItem(user, Colors.BG_DARK)
                user_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                row_items.append(user_item)

                # Calculate values and ranks
                columns_data: List[ColumnData] = [
                    ColumnData(
                        value=user_stats.active,
                        rank=_get_rank(user_stats.active, [s.active for s in all_stats]),
                    ),
                    ColumnData(
                        value=user_stats.merged,
                        rank=_get_rank(user_stats.merged, [s.merged for s in all_stats]),
                    ),
                    ColumnData(
                        value=user_stats.commented,
                        rank=_get_rank(user_stats.commented, [s.commented for s in all_stats]),
                    ),
                    ColumnData(
                        value=user_stats.avg_lines_added,
                        rank=_get_rank(user_stats.avg_lines_added, [s.avg_lines_added for s in all_stats]),
                    ),
                    ColumnData(
                        value=user_stats.avg_pr_age_days,
                        rank=_get_rank(user_stats.avg_pr_age_days, [s.avg_pr_age_days for s in all_stats]),
                        reverse=True
                    ),
                    ColumnData(
                        value=user_stats.avg_time_to_merge_days,
                        rank=_get_rank(user_stats.avg_time_to_merge_days,
                                       [s.avg_time_to_merge_days for s in all_stats]),
                        reverse=True
                    ),
                    ColumnData(
                        value=user_stats.avg_time_since_comment_days,
                        rank=_get_rank(user_stats.avg_time_since_comment_days,
                                       [s.avg_time_since_comment_days for s in all_stats]),
                        reverse=True
                    ),
                    ColumnData(
                        value=user_stats.avg_commits,
                        rank=_get_rank(user_stats.avg_commits, [s.avg_commits for s in all_stats]),
                    ),
                ]

                # Create items for stats columns
                for col_data in columns_data:
                    # Get the background color
                    bg_color = _get_gradient_color(col_data.rank, col_data.reverse)
                    text_color = _get_text_color(bg_color)

                    # Create colored item
                    item = ColoredTableItem(
                        text=str(col_data.value),
                        background_color=bg_color,
                        text_color=text_color
                    )
                    item.setData(Qt.ItemDataRole.UserRole, float(col_data.value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    row_items.append(item)

                # Set all items for this row at once
                for col, item in enumerate(row_items):
                    self.table.setItem(row_idx, col, item)

        finally:
            # Re-enable sorting
            self.table.setSortingEnabled(True)

        # Update heatmap
        matrix, authors, commenters = self._calculate_comment_heatmap(selected_period_days)
        self._update_heatmap(matrix, authors, commenters)

        # Sort by Active PRs column by default (descending)
        self.table.sortItems(1, Qt.SortOrder.DescendingOrder)

        # Adjust column widths
        self.table.resizeColumnsToContents()

    def _on_tab_changed(self, index):
        """Handle tab changes"""
        if index == 1 and not self.heatmap_initialized:  # Heatmap tab
            QTimer.singleShot(0, self._initialize_heatmap)

    def _initialize_heatmap(self):
        """Lazy initialization of matplotlib/seaborn components"""
        try:
            # Import visualization libraries only when needed
            import matplotlib
            matplotlib.use('Qt5Agg')
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            import seaborn as sns

            # Create matplotlib figure
            self.figure = Figure(figsize=(12, 8))
            self.canvas = FigureCanvasQTAgg(self.figure)
            self.canvas.setStyleSheet(f"""
                background-color: {Colors.BG_DARKER};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: 8px;
            """)

            # Remove loading message and add canvas
            self.heatmap_layout.addWidget(self.canvas)

            self.heatmap_initialized = True

            # Update the heatmap
            self.update_stats()

        except Exception as e:
            print(f"Error initializing heatmap: {e}")
            traceback.print_exc()

    def closeEvent(self, event):
        """Handle dialog close event"""
        try:
            # Close the matplotlib figure to free up resources
            plt.close(self.figure)

            # Clear any matplotlib state
            plt.clf()

            # Delete the canvas explicitly
            if self.canvas:
                self.canvas.deleteLater()

        except Exception as e:
            print(f"Error during stats dialog cleanup: {e}")
            traceback.print_exc()
        finally:
            # Accept the close event
            event.accept()
