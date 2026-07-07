from PySide6.QtWidgets import QMainWindow, QDockWidget, QLabel, QSizePolicy, QPushButton
from PySide6.QtCore import Qt
from console.ros_nodes.mediator import Mediator
from console.gui.camera_display import CameraDisplay
from console.gui.status_widget import StatusWidget
from console.gui.motor_currents import MotorCurrents

class MainTab(QMainWindow):
    def __init__(self, mediator: Mediator, parent=None):
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

        self._motor_currents = MotorCurrents(self._mediator)
        self._motor_currents.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self._motor_dock = self._create_dock("Motor Currents", self._motor_currents)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self._motor_dock)

        self._cam = CameraDisplay(self._mediator, self)
        self._cam.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._cam_dock = self._create_dock("Camera", self._cam)
        self.splitDockWidget(self._motor_dock, self._cam_dock, Qt.Orientation.Horizontal)

        self._battery_status = StatusWidget("batteries.qml", self._mediator, self)
        self._battery_dock = self._create_dock("Battery Status", self._battery_status)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._battery_dock)

        self._speedometer = StatusWidget("speedometer.qml", self._mediator, self)
        self._speedometer_dock = self._create_dock("Speedometer", self._speedometer)
        self.splitDockWidget(self._battery_dock, self._speedometer_dock, Qt.Orientation.Horizontal)

        self._compass = StatusWidget("compass.qml", self._mediator, self)
        self._compass_dock = self._create_dock("Compass", self._compass)
        self.splitDockWidget(self._speedometer_dock, self._compass_dock, Qt.Orientation.Horizontal)

        self._position = QLabel("Position: 0, 0")
        self._mediator.telemetry_updated.connect(self.update_position)
        self.statusBar().addPermanentWidget(self._position)

        self._auto = False
        #self._mediator.set_auto(self._auto)
        self._mode_button = QPushButton('Switch to automatic')
        self._mode_button.clicked.connect(self._switch_mode)
        self.statusBar().addPermanentWidget(self._mode_button)

        self.resizeDocks([self._motor_dock, self._cam_dock], [50, 500], Qt.Orientation.Horizontal)

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

    def _switch_mode(self):
        if self._auto:
            self._auto = False
            #self._mediator.set_auto(self._auto)
            self._mode_button.setText('Switch to automatic')
        else:
            self._auto = True
            #self._mediator.set_auto(self._auto)
            self._mode_button.setText('Switch to manual')

    
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