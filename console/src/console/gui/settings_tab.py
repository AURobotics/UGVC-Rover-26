from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QGroupBox, QComboBox, QSpacerItem

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

        self._joy_select = QComboBox()
        self._joy_select.setPlaceholderText("Select controller")
        self._joy_select.setCurrentIndex(-1)
        self._joy_select.setToolTip("Select the joystick controller to use for driving the rover.")
        self._selection_setup()
        self._joy_select.currentIndexChanged.connect(self._on_joy_change)
        self._mediator.controller_changed.connect(self._selection_setup)
        self._joy_layout.addWidget(self._joy_select)

        self._layout.addWidget(self._joy_group)

        spacer2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._layout.addItem(spacer2)

    def _selection_setup(self, controller_info: dict[str, str] | None = None):
        self._joy_select.blockSignals(True)

        self._joy_select.clear()
        controllers = self._mediator.get_available_controllers()
        active_controller = self._mediator.get_active_controller()

        for controller in controllers:
            self._joy_select.addItem(controller["name"], controller["guid"])

        if active_controller is not None:
            idx = self._joy_select.findData(active_controller["guid"])
            self._joy_select.setCurrentIndex(idx)
        else:
            self._joy_select.setCurrentIndex(-1)

        self._joy_select.blockSignals(False)

    def _on_joy_change(self, index: int):
        if index < 0:
            return
        guid = self._joy_select.itemData(index)
        if guid is not None:
            self._mediator.select_controller_by_guid(guid)