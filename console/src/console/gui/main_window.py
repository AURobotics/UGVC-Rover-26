from PySide6.QtWidgets import QMainWindow

from console.ros_nodes.worker import ROS2Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UGVC Rover 26 Console")
        self.ros2 = ROS2Worker(self)
        self.ros2.start()