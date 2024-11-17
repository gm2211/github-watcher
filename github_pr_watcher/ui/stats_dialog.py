from datetime import datetime, timedelta
from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QComboBox,
    QHBoxLayout,
    QWidget,
)

from github_pr_watcher.ui.themes import Colors, Styles


class StatsDialog(QDialog):
    def __init__(self, ui_state, parent=None):
        super().__init__(parent)
        self.ui_state = ui_state
        self.setWindowTitle("User Statistics")
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")
        self.setMinimumSize(800, 400)
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create period selector
        period_container = QWidget()
        period_layout = QHBoxLayout(period_container)
        period_layout.setContentsMargins(0, 0, 0, 10)
        
        period_label = QLabel("Time Period:")
        period_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last Week", "Last Month", "Last 3 Months"])
        self.period_combo.setStyleSheet(Styles.COMBO_BOX)
        self.period_combo.currentTextChanged.connect(self.update_stats)
        
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()
        
        layout.addWidget(period_container)
        
        # Create table
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                gridline-color: #373e47;
                border: 1px solid #373e47;
                border-radius: 6px;
            }
            QTableWidget::item {
                background-color: transparent;
                padding: 5px;
                border: none;
            }
            QHeaderView::section {
                background-color: #1c2128;
                background-color: transparent;
                color: #e6edf3;
                padding: 5px;
                border: none;
                border-right: 1px solid #373e47;
                border-bottom: 1px solid #373e47;
            }
        """)
        
        # Set up columns
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "User",
            "PRs Created",
            "PRs Merged",
            "PRs Reviewed",
            "Active PRs"
        ])
        
        # Adjust column widths
        self.table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table)
        
        # Initial update
        self.update_stats()

    def _get_period_days(self) -> int:
        period = self.period_combo.currentText()
        if period == "Last Week":
            return 7
        elif period == "Last Month":
            return 30
        else:  # Last 3 Months
            return 90

    def _calculate_user_stats(self, days: int) -> List[Dict]:
        cutoff_date = datetime.now().astimezone() - timedelta(days=days)
        stats = {}
        
        # Process each section's PRs
        for section_data in self.ui_state.data_by_section.values():
            if not section_data:
                continue
                
            for user_prs in section_data.prs_by_author.values():
                for pr in user_prs:
                    author = pr.user.login
                    
                    # Initialize stats for new users
                    if author not in stats:
                        stats[author] = {
                            "created": 0,
                            "merged": 0,
                            "reviewed": 0,
                            "active": 0,
                            "weeks": days / 7,  # Convert days to weeks
                        }
                    
                    # Count created PRs
                    if pr.created_at >= cutoff_date:
                        stats[author]["created"] += 1
                    
                    # Count merged PRs
                    if pr.merged and pr.merged_at and pr.merged_at >= cutoff_date:
                        stats[author]["merged"] += 1
                    
                    # Count active PRs (open and not archived)
                    if pr.state.lower() == "open" and not pr.archived:
                        stats[author]["active"] += 1
                    
                    # Count reviewed PRs (PRs where the user commented but isn't the author)
                    for commenter in (pr.comment_count_by_author or {}).keys():
                        if commenter != author and commenter not in stats:
                            stats[commenter] = {
                                "created": 0,
                                "merged": 0,
                                "reviewed": 0,
                                "active": 0,
                                "weeks": days / 7,
                            }
                        if commenter != author and pr.last_comment_time and pr.last_comment_time >= cutoff_date:
                            stats[commenter]["reviewed"] += 1

        # Convert to list and calculate per-week averages
        result = []
        for user, user_stats in stats.items():
            weeks = max(1, user_stats["weeks"])  # Avoid division by zero
            result.append({
                "user": user,
                "created_per_week": round(user_stats["created"] / weeks, 1),
                "merged_per_week": round(user_stats["merged"] / weeks, 1),
                "reviewed_per_week": round(user_stats["reviewed"] / weeks, 1),
                "active": user_stats["active"],
            })
        
        # Sort by PRs created per week
        result.sort(key=lambda x: x["created_per_week"], reverse=True)
        return result

    def update_stats(self):
        days = self._get_period_days()
        stats = self._calculate_user_stats(days)
        
        # Update table
        self.table.setRowCount(len(stats))
        
        for row, user_stats in enumerate(stats):
            # User
            user_item = QTableWidgetItem(user_stats["user"])
            user_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, user_item)
            
            # PRs Created/Week
            created_item = QTableWidgetItem(str(user_stats["created_per_week"]))
            created_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, created_item)
            
            # PRs Merged/Week
            merged_item = QTableWidgetItem(str(user_stats["merged_per_week"]))
            merged_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, merged_item)
            
            # PRs Reviewed/Week
            reviewed_item = QTableWidgetItem(str(user_stats["reviewed_per_week"]))
            reviewed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, reviewed_item)
            
            # Active PRs
            active_item = QTableWidgetItem(str(user_stats["active"]))
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, active_item)
        
        # Adjust column widths
        self.table.resizeColumnsToContents() 