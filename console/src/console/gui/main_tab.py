from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel
from PySide6.QtCore import Qt, QTimer
from console.gui.camera_display import CameraDisplay
from console.gui.status_widget import StatusWidget

class MainTab(QMainWindow):
    def __init__(self, mediator, parent=None):
        super().__init__(parent)

        self._mediator = mediator

        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.GroupedDragging
            | QMainWindow.DockOption.VerticalTabs
        )

        self._cam = CameraDisplay(self._mediator, self)
        self._cam_dock = self._create_dock("Camera", self._cam)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self._cam_dock)

        self._battery_status = StatusWidget("batteries.qml", self._mediator, self)
        self._battery_dock = self._create_dock("Battery Status", self._battery_status)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._battery_dock)

        self._speedometer = StatusWidget("speedometer.qml", self._mediator, self)
        self._speedometer_dock = self._create_dock("Speedometer", self._speedometer)
        self.splitDockWidget(self._battery_dock, self._speedometer_dock, Qt.Orientation.Horizontal)

        self._compass = StatusWidget("compass.qml", self._mediator, self)
        self._compass_dock = self._create_dock("Compass", self._compass)
        self.splitDockWidget(self._battery_dock, self._compass_dock, Qt.Orientation.Horizontal)

        self._position = QLabel("Position: 0, 0")
        self.statusBar().addPermanentWidget(self._position)
        self._mediator.telemetry_updated.connect(self.update_position)

    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock
    
    def update_position(self): #temporary, until we finalize subscriptions
        lat = self._mediator.latitude
        lon = self._mediator.longitude
        self._position.setText(f"Position: {lat:.2f}, {lon:.2f}")
    
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