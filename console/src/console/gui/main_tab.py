from PySide6.QtWidgets import QMainWindow, QDockWidget
from PySide6.QtCore import Qt
from console.gui.camera_display import CameraDisplay

class MainTab(QMainWindow):
    def __init__(self, mediator, parent=None):
        super().__init__(parent)

        self.mediator = mediator

        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.GroupedDragging
            | QMainWindow.DockOption.VerticalTabs
        )

        self._cam = CameraDisplay(self.mediator, self)
        self._cam_dock = self._create_dock("Camera", self._cam)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self._cam_dock)

    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock
    
    def hideEvent(self, event):
        super().hideEvent(event)
        for dock in self.findChildren(QDockWidget):
            if dock.isFloating():
                dock.hide()

    def showEvent(self, event):
        super().showEvent(event)
        for dock in self.findChildren(QDockWidget):
            if dock.isFloating():
                dock.show()