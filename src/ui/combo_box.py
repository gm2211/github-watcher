from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QComboBox, QListView


class MultiSelectComboBox(QComboBox):
    selectionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = {"All Authors"}
        
        # Create and set model
        self._model = QStandardItemModel()
        self.setModel(self._model)
        
        # Setup view
        view = QListView()
        view.setMinimumWidth(200)
        self.setView(view)
        
        # Style setup
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #373e47;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: #1c2128;
            }
            QComboBox:hover {
                border-color: #58a6ff;
                background-color: #2d333b;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1c2128;
                border: 1px solid #373e47;
                border-radius: 6px;
                selection-background-color: transparent;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                min-height: 24px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2d333b;
            }
        """)
        
        # Initial setup
        self.setEditable(False)
        
        # Connect signals
        self._model.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        """Handle checkbox state changes"""
        text = item.text()
        checked = item.checkState() == Qt.CheckState.Checked

        if text == "All Authors":
            if checked:
                # Select only "All Authors"
                self._selected = {"All Authors"}
                # Update all other checkboxes
                for row in range(1, self._model.rowCount()):
                    self._model.item(row).setCheckState(Qt.CheckState.Unchecked)
        else:
            if checked:
                # Add to selection and uncheck "All Authors"
                self._selected.add(text)
                self._selected.discard("All Authors")
                if all_authors := self._model.item(0):
                    all_authors.setCheckState(Qt.CheckState.Unchecked)
            else:
                # Remove from selection
                self._selected.discard(text)
                # If nothing selected, select "All Authors"
                if len(self._selected) == 0:
                    self._selected = {"All Authors"}
                    if all_authors := self._model.item(0):
                        all_authors.setCheckState(Qt.CheckState.Checked)

        self._update_display()
        self.selectionChanged.emit()

    def _update_display(self):
        """Update the display text"""
        if "All Authors" in self._selected:
            self.setCurrentText("All Authors")
        else:
            selected = sorted(self._selected)
            if len(selected) <= 2:
                self.setCurrentText(", ".join(selected))
            else:
                self.setCurrentText(f"{selected[0]}, {selected[1]} (+{len(selected)-2})")

    def addItems(self, items):
        """Add items to the combo box"""
        self._model.clear()
        self._selected = {"All Authors"}
        
        for text in items:
            item = QStandardItem(text)
            item.setCheckState(Qt.CheckState.Checked if text == "All Authors" else Qt.CheckState.Unchecked)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            self._model.appendRow(item)
        
        self._update_display()

    def get_selected_items(self):
        """Get currently selected items"""
        return self._selected.copy()

    def clear(self):
        """Clear all items"""
        self._model.clear()
        self._selected = {"All Authors"}
        self.setCurrentText("All Authors")
