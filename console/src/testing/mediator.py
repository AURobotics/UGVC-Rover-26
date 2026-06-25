from console.ros_nodes.worker import ROS2Worker

class Mediator:
    def __init__(self):
        super().__init__()
        self.telemetry_exists = False
        self._worker_thread = ROS2Worker()
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
        self.telemetry_exists = True

    def get_frame(self):
        if self.telemetry_exists:
            return self.lane_bev_image
        return None