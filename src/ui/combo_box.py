from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QComboBox, QListView


class MultiSelectComboBox(QComboBox):
    selectionChanged = pyqtSignal()

    def __init__(self, default_selection):
        super().__init__(None)
        self.default_selection = default_selection
        self._selected = {self.default_selection}

        # Create and set model
        self._model: QStandardItemModel = QStandardItemModel()
        self.setModel(self._model)

        # Setup view
        view = QListView()
        view.setMinimumWidth(200)
        self.setView(view)

        # Initial setup
        self.setEditable(False)

        # Connect signals
        self._model.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        """Handle checkbox state changes"""
        text = item.text()
        checked = item.checkState() == Qt.CheckState.Checked

        if text == self.default_selection:
            if checked:
                # Select only ALL_AUTHORS
                self._selected = {self.default_selection}
                # Update all other checkboxes
                for row in range(1, self._model.rowCount()):
                    self._model.item(row).setCheckState(Qt.CheckState.Unchecked)
        else:
            if checked:
                # Add to selection and uncheck ALL_AUTHORS
                self._selected.add(text)
                self._selected.discard(self.default_selection)
                if all_authors := self._model.item(0):
                    all_authors.setCheckState(Qt.CheckState.Unchecked)
            else:
                # Remove from selection
                self._selected.discard(text)
                # If nothing selected, select ALL_AUTHORS
                if len(self._selected) == 0:
                    self._selected = {self.default_selection}
                    if all_authors := self._model.item(0):
                        all_authors.setCheckState(Qt.CheckState.Checked)

        self._update_display()
        self.selectionChanged.emit()

    def _update_display(self):
        """Update the display text"""
        if self.default_selection in self._selected:
            self.setCurrentText(self.default_selection)
        else:
            selected = sorted(self._selected)
            if len(selected) <= 2:
                self.setCurrentText(", ".join(selected))
            else:
                self.setCurrentText(
                    f"{selected[0]}, {selected[1]} (+{len(selected)-2})"
                )

    def addItems(self, items):
        """Add items to the combo box"""
        self._model.clear()
        self._selected = {self.default_selection}

        for text in items:
            item = QStandardItem(text)
            item.setCheckState(
                Qt.CheckState.Checked
                if text == self.default_selection
                else Qt.CheckState.Unchecked
            )
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            self._model.appendRow(item)

        self._update_display()

    def get_selected_items(self):
        """Get currently selected items"""
        return self._selected.copy()

    def clear(self):
        """Clear all items"""
        self._model.clear()
        self._selected = {self.default_selection}
        self.setCurrentText(self.default_selection)
