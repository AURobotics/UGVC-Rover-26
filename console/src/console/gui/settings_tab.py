from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout, QHBoxLayout,
    QSizePolicy,
    QGroupBox, QComboBox,
    QSpacerItem,
    QLabel, QSlider, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from console.ros_nodes.mediator import Mediator

class SettingsTab(QWidget):
    def __init__(self, mediator: Mediator, parent=None):
        super().__init__(parent)

        self._mediator = mediator

        self._layout = QVBoxLayout(self)

        spacer1 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._layout.addItem(spacer1)

        self._joy_group = QGroupBox("Joystick Controls")
        self._joy_layout = QVBoxLayout(self._joy_group)

        self._joy_select = JoySelectComboBox(self._mediator)
        self._joy_layout.addWidget(self._joy_select)

        self._deadzone_label = QLabel("Deadzone:")
        self._joy_layout.addWidget(self._deadzone_label)
        self._deadzone_settings = DeadzoneSettings(self._mediator)
        self._joy_layout.addWidget(self._deadzone_settings)

        self._layout.addWidget(self._joy_group)

        spacer2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._layout.addItem(spacer2)


class JoySelectComboBox(QComboBox):
    def __init__(self, mediator: Mediator, parent=None):
        super().__init__(parent)
        self._mediator = mediator
        self.setPlaceholderText("Select controller")
        self.setCurrentIndex(-1)
        self.setToolTip("Select the joystick controller to use for driving the rover.")
        self._selection_setup()
        self.currentIndexChanged.connect(self._on_joy_change)
        self._mediator.controller_changed.connect(self._selection_setup)

    def _selection_setup(self, controller_info: dict[str, str] | None = None):
        self.blockSignals(True)

        self.clear()
        controllers = self._mediator.get_available_controllers()
        active_controller = self._mediator.get_active_controller()

        for controller in controllers:
            self.addItem(controller["name"], controller["guid"])

        if active_controller is not None:
            idx = self.findData(active_controller["guid"])
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(-1)

        self.blockSignals(False)

    def _on_joy_change(self, index: int):
        if index < 0:
            return
        guid = self.itemData(index)
        if guid is not None:
            self._mediator.select_controller_by_guid(guid)

class DeadzoneSettings(QWidget):
    def __init__(self, mediator: Mediator, parent=None):
        super().__init__(parent)
        self._mediator = mediator

        self._layout = QHBoxLayout(self)

        self._deadzone_value = QLineEdit('0.00')
        self._deadzone_value.setStyleSheet("background-color: transparent; border: none;")
        self._deadzone_value.setFixedWidth(50)
        self._deadzone_value.setValidator(QDoubleValidator(0.00, 1.00, 2, self))
        self._deadzone_value.editingFinished.connect(self._on_deadzone_value_changed)
        self._layout.addWidget(self._deadzone_value)

        self._deadzone_slider = QSlider(Qt.Orientation.Horizontal)
        self._deadzone_slider.setRange(0, 100)
        self._deadzone_slider.valueChanged.connect(self._on_deadzone_slider_changed)
        self._layout.addWidget(self._deadzone_slider)

    def _on_deadzone_value_changed(self):
        text = self._deadzone_value.text()
        try:
            value = float(text)
        except ValueError:
            #self._deadzone_value.setText(f"{self._mediator.get_joystick_deadzone():.2f}") #temporary
            return
        if 0.0 <= value <= 1.0:
            slider_value = int(value * 100)
            self._deadzone_slider.setValue(slider_value)
            #self._mediator.set_joystick_deadzone(value) #temporary
        else:
            ...
            #self._deadzone_value.setText(f"{self._mediator.get_joystick_deadzone():.2f}") #temporary

    def _on_deadzone_slider_changed(self, value: int):
        deadzone_value = value / 100.0
        self._deadzone_value.setText(f"{deadzone_value:.2f}")
        #self._mediator.set_joystick_deadzone(deadzone_value) #temporary