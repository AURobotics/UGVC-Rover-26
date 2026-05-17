from PySide6.QtWidgets import QApplication
from console.gui.main_window import MainWindow

def main():
    app = QApplication()
    main_window = MainWindow()
    main_window.show()
    app.exec()