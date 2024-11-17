from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
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
)

from github_pr_watcher.objects import PullRequest
from github_pr_watcher.settings import Settings
from github_pr_watcher.ui.themes import Colors, Styles

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

    def to_display_stats(self) -> Dict:
        """Convert raw stats to display format"""
        total_prs = max(1, self.total_prs)  # Avoid division by zero
        total_merged = max(1, self.total_merged_prs)  # Avoid division by zero

        return {
            "user": self.user,
            "created_per_week": self.created,
            "merged_per_week": self.merged,
            "commented_per_week": self.commented,
            "active": self.active,
            "avg_lines_added": round(self.total_lines_added / total_prs),
            "avg_pr_age": round(self.total_pr_age.total_seconds() / (total_prs * SECONDS_PER_DAY), 1),
            "avg_time_to_merge": round(self.total_time_to_merge.total_seconds() / (total_merged * SECONDS_PER_DAY), 1),
            "avg_time_since_comment": round(
                self.total_time_since_comment.total_seconds() / (total_prs * SECONDS_PER_DAY), 1),
            "avg_commits": round(self.total_commits / total_prs, 1) if self.total_commits > 0 else 0,
        }


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

        # Create period selector in a styled frame
        period_frame = StyledFrame()
        period_layout = QHBoxLayout(period_frame)
        period_layout.setContentsMargins(0, 0, 0, 0)

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

        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()

        layout.addWidget(period_frame)

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
                background-color: #1c2128;
                gridline-color: #373e47;
                border: 1px solid #373e47;
                border-radius: 6px;
            }}
            QTableWidget::item {{
                background-color: #1c2128;
                padding: 5px;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_DARKER};
                padding: 5px;
                border: none;
                border-right: 1px solid #373e47;
                border-bottom: 1px solid #373e47;
            }}
            QHeaderView::section:hover {{
                background-color: {Colors.BG_LIGHT};
            }}
        """)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)  # Enable sorting
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make table read-only

        # Set up columns
        self.columns = [
            ("User", str),
            ("PRs Created", float),
            ("PRs Merged", float),
            ("PRs commented", float),
            ("Active PRs", int),
            ("Avg Lines Added", int),
            ("Avg PR Age (days)", float),
            ("Avg TTM (days)", float),
            ("Avg TSLC (days)", float),
            ("Avg Commits", float)
        ]
        table.setColumnCount(len(self.columns))
        table.setHorizontalHeaderLabels([col[0] for col in self.columns])

        # Set column stretch behavior
        table.horizontalHeader().setStyleSheet("background-color: transparent;")

        # All columns get equal stretch
        for i in range(len(self.columns)):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        return table

    def _calculate_user_stats(self, selected_period_days: int) -> List[UserStats]:
        """Calculate user statistics - only for configured users"""
        cutoff_date = datetime.now().astimezone() - timedelta(days=selected_period_days)
        stats_by_user: Dict[str, UserStats] = {}

        # Initialize stats for all configured users
        for user in sorted(set(self.settings.users)):
            stats_by_user[user] = UserStats(user=user)

        now = datetime.now().astimezone()

        # Process each section's PRs
        processed_prs = set()  # Track processed PRs to avoid duplicates
        for section_data in self.ui_state.data_by_section.values():
            if not section_data:
                continue

            for author, prs in section_data.prs_by_author.items():
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

        # Convert to list and sort by total PRs created
        result = list(stats_by_user.values())
        result.sort(key=lambda x: x.created, reverse=True)
        return result

    def _calculate_comment_heatmap(self, selected_period_days: int) -> Tuple[np.ndarray, List[str], List[str]]:
        """Calculate comment frequency between authors and commenters"""
        cutoff_date = datetime.now().astimezone() - timedelta(days=selected_period_days)
        comment_counts = {}  # author -> commenter -> count
        all_commenters = set()  # Track all users who have commented

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

                    # Count comments (using comments as a proxy)
                    for commenter, count in (pr.comment_count_by_author or {}).items():
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
        stats = self._calculate_user_stats(selected_period_days)
        self.table.setRowCount(len(stats))

        for row, user_stats in enumerate(stats):
            display_stats = user_stats.to_display_stats()
            columns = [
                (user_stats.user, Qt.AlignmentFlag.AlignLeft),
                (display_stats["created_per_week"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["merged_per_week"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["commented_per_week"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["active"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["avg_lines_added"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["avg_pr_age"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["avg_time_to_merge"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["avg_time_since_comment"], Qt.AlignmentFlag.AlignCenter),
                (display_stats["avg_commits"], Qt.AlignmentFlag.AlignCenter),
            ]

            for col, (value, alignment) in enumerate(columns):
                item = QTableWidgetItem()
                # Store the actual value for sorting
                item.setData(Qt.ItemDataRole.UserRole, value)
                # Display formatted value
                if isinstance(value, (int, float)):
                    item.setText(f"{value:.1f}" if isinstance(value, float) else str(value))
                else:
                    item.setText(str(value))
                item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

        # Update heatmap (all commenters)
        matrix, authors, commenters = self._calculate_comment_heatmap(selected_period_days)
        self._update_heatmap(matrix, authors, commenters)

        # Sort by PRs Created column by default (descending)
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
        finally:
            # Accept the close event
            event.accept()
