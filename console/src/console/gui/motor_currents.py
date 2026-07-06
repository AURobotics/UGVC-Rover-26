from PySide6.QtWidgets import QWidget, QGridLayout, QLabel
from PySide6.QtCore import Qt
from console.ros_nodes.mediator import Mediator

class MotorCurrents(QWidget):
    def __init__(self, mediator: Mediator, parent: QWidget | None =None):
        super().__init__(parent)
        self._mediator = mediator

        self._layout = QGridLayout(self)

        self._fl_current = QLabel('0.00 A') #current of the front left motor
        self._layout.addWidget(self._fl_current, 0, 0)

        self._fr_current = QLabel('0.00 A') #current of the front right motor
        self._layout.addWidget(self._fr_current, 0, 1)

        self._bl_current = QLabel('0.00 A') #current of the back left motor
        self._layout.addWidget(self._bl_current, 1, 0)

        self._br_current = QLabel('0.00 A') #current of the back right motor
        self._layout.addWidget(self._br_current, 1, 1)

        for label in [self._fl_current, self._fr_current, self._bl_current, self._br_current]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    background-color: #2C3E50;
                    border: 2px solid #34495E;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

        self._mediator.telemetry_updated.connect(self._update_currents)

    def _update_currents(self):
        ...