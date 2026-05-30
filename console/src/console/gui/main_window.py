from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QTimer
from console.ros_nodes.worker import ROS2RoverWorker
from console.gui.camera_display import CameraDisplay

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UGVC Rover 26 Console")

        self._cam = CameraDisplay()
        self.setCentralWidget(self._cam)
        self._cam_timer = QTimer(self)
        self._cam_timer.timeout.connect(self.update_camera_display)
        self._cam_timer.start(33)
        self._worker_thread = ROS2RoverWorker()
        self._worker_thread.signals.telemetry_received.connect(self.handle_telemetry)
        self._worker_thread.start()

    def handle_telemetry(self, telemetry: dict) -> None:
        self.status_state = telemetry.get("status_state", "Unknown")
        self.latitude = telemetry.get("latitude", 0.0)
        self.longitude = telemetry.get("longitude", 0.0)
        self.battery_voltage = telemetry.get("battery_voltage", 0.0)
        self.left_motor_voltage = telemetry.get("left_motor_voltage", 0.0)
        self.right_motor_voltage = telemetry.get("right_motor_voltage", 0.0)
        self.battery_percent = telemetry.get("battery_percent", 0.0)
        self.imu_accel_z = telemetry.get("imu_accel_z", 0.0)
        self.lane_bev_image = telemetry.get("lane_bev_image", None)

    def update_camera_display(self):
        if self.lane_bev_image is not None:
            self._cam.update_frame(self.lane_bev_image)