from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QGroupBox, QComboBox, QSpacerItem

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)

        spacer1 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._layout.addItem(spacer1)

        self._joy_group = QGroupBox("Joystick Controls")
        self._joy_layout = QVBoxLayout(self._joy_group)

        self._joy_select = QComboBox()
        self._joy_layout.addWidget(self._joy_select)

        self._layout.addWidget(self._joy_group)

        spacer2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self._layout.addItem(spacer2)