from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QUrl
from console.assets import get_asset

class StatusWidget(QWidget):
    def __init__(self, widget_filepath: str, data_bridge = None, parent: QWidget | None = None):
        super().__init__(parent)

        self._data_bridge = data_bridge

        self._layout = QVBoxLayout(self)
        self._view = QQuickWidget()
        
        self._view.setInitialProperties({"rover": self._data_bridge})
        
        self._view.setSource(QUrl.fromLocalFile(get_asset(widget_filepath)))
        
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._layout.addWidget(self._view)