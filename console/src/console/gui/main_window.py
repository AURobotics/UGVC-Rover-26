from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QWidget, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup

from console.gui.main_tab import MainTab
from console.gui.settings_tab import SettingsTab

from console.ros_nodes.mediator import Mediator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UGVC Rover 26 Console")

        self.mediator = Mediator()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        main_tab = MainTab(self.mediator)
        settings_tab = SettingsTab(self.mediator)

        self.stack = QStackedWidget()
        self.stack.addWidget(main_tab)
        self.stack.addWidget(settings_tab)
        self.setCentralWidget(self.stack)

        self.sidebar = QToolBar()
        self.sidebar.setIconSize(QSize(24, 24))
        self.sidebar.setMovable(False)
        self.sidebar.setStyleSheet("""
            QToolBar {
                border-right: 1px solid #555555;
                spacing: 10px;
                padding: 5px;
            }

            QToolButton {
                color: white;
                background-color: transparent;
                border-radius: 4px;
                padding: 8px;
            }
            
            QToolButton:hover {
                background-color: #3d3d3d;
            }

            QToolButton:checked {
                background-color: #0078d7;
                font-weight: bold;
            }
        """)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.sidebar)

        self.sidebar_actions = QActionGroup(self)
        self.sidebar_actions.setExclusive(True)

        for i, name in enumerate(["Main", "Settings"]):
            self._setup_action(i, name)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.sidebar.insertWidget(self.sidebar.actions()[-1], spacer)

        hide_action = self.sidebar.toggleViewAction()
        hide_action.setText("Hide sidebar")
        hide_action.setShortcut("Ctrl+B")
        hide_action.triggered.connect(
            lambda: hide_action.setText(
                f"{'Show' if self.sidebar.isHidden() else 'Hide'} sidebar"
            )
        )
        self.sidebar.setToolTip("Toggle visibility with Ctrl+B")
        self.menuBar().addAction(hide_action)

    def _setup_action(self, idx, name):
        action = QAction(name, self, checkable=True)
        action.setData(idx)
        self.sidebar_actions.addAction(action)
        self.sidebar.addAction(action)
        action.triggered.connect(lambda _: self.stack.setCurrentIndex(action.data()))
        if idx == 0:
            action.setChecked(True)

    def closeEvent(self, event):
        self.mediator.stop()
        super().closeEvent(event)