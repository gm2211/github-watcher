from PyQt6.QtWidgets import QComboBox, QListView, QStyledItemDelegate
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem

class MultiSelectComboBox(QComboBox):
    selectionChanged = pyqtSignal()  # Signal when selection changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = set()
        self._selected = {"All Authors"}
        self._is_updating = False
        
        # Create model
        self._model = QStandardItemModel()
        self.setModel(self._model)
        
        # Setup view
        list_view = QListView()
        list_view.setSelectionMode(QListView.SelectionMode.SingleSelection)
        list_view.setMinimumWidth(200)
        self.setView(list_view)
        
        # Initial setup
        self.setEditable(False)
        
        # Connect signals
        self.view().clicked.connect(self._handle_click)
        
    def _handle_click(self, index):
        """Handle item click"""
        if self._is_updating:
            return
            
        self._is_updating = True
        try:
            item = self._model.itemFromIndex(index)
            if not item:
                return
                
            text = item.text()
            if text == "All Authors":
                # Clear all other selections
                self._selected = {"All Authors"}
                for i in range(self._model.rowCount()):
                    if model_item := self._model.item(i):
                        model_item.setCheckState(
                            Qt.CheckState.Checked if i == 0 
                            else Qt.CheckState.Unchecked
                        )
            else:
                # Handle individual author selection
                if text in self._selected:
                    self._selected.discard(text)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    if not self._selected:
                        # If nothing selected, select "All Authors"
                        self._selected = {"All Authors"}
                        if all_authors := self._model.item(0):
                            all_authors.setCheckState(Qt.CheckState.Checked)
                else:
                    self._selected.add(text)
                    item.setCheckState(Qt.CheckState.Checked)
                    # Uncheck "All Authors"
                    if "All Authors" in self._selected:
                        self._selected.discard("All Authors")
                        if all_authors := self._model.item(0):
                            all_authors.setCheckState(Qt.CheckState.Unchecked)
                    
            self._update_display()
            self.selectionChanged.emit()
            
        finally:
            self._is_updating = False
            
    def _update_display(self):
        """Update the display text"""
        if "All Authors" in self._selected:
            self.setCurrentText("All Authors")
        else:
            self.setCurrentText(", ".join(sorted(self._selected)))
            
    def addItems(self, items):
        """Add multiple items to the combo box"""
        if self._is_updating:
            return
            
        self._is_updating = True
        try:
            self._model.clear()
            self._items.clear()
            self._selected = {"All Authors"}
            
            for text in items:
                if text and isinstance(text, str):
                    self._items.add(text)
                    item = QStandardItem(text)
                    item.setCheckState(
                        Qt.CheckState.Checked if text == "All Authors"
                        else Qt.CheckState.Unchecked
                    )
                    self._model.appendRow(item)
                    
            self._update_display()
            
        finally:
            self._is_updating = False
            
    def clear(self):
        """Clear all items"""
        if self._is_updating:
            return
            
        self._is_updating = True
        try:
            self._model.clear()
            self._items.clear()
            self._selected = {"All Authors"}
            self.setCurrentText("All Authors")
        finally:
            self._is_updating = False
            
    def getSelectedItems(self):
        """Get the currently selected items"""
        return self._selected.copy()