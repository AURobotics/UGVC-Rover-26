from PySide6.QtWidgets import QMainWindow, QDockWidget
from PySide6.QtCore import Qt
from console.gui.camera_display import CameraDisplay
from console.gui.status_widget import StatusWidget

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

        self._battery_status = StatusWidget("batteries.qml", self.mediator, self)
        self._battery_dock = self._create_dock("Battery Status", self._battery_status)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._battery_dock)

        self._speedometer = StatusWidget("speedometer.qml", self.mediator, self)
        self._speedometer_dock = self._create_dock("Speedometer", self._speedometer)
        self.splitDockWidget(self._battery_dock, self._speedometer_dock, Qt.Orientation.Horizontal)

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