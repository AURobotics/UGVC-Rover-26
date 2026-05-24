#! /usr/bin/env python3
from PySide6.QtCore import QObject, QThread, Signal
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image, Imu, NavSatFix
from std_msgs.msg import Float32MultiArray, String

class RoverSignals(QObject):
    telemetry_received = Signal(dict)

class WorkerNode(Node):
    GUI_EMIT_INTERVAL_SEC = 0.1  

    IMAGE_TOPICS = (
        "rover/camera/front",
        "rover/camera/rear",
        "rover/debug/lane_bev",
        "rover/debug/lane_trace",
        "rover/debug/face",
    )

    def __init__(self, signals: RoverSignals):
        super().__init__("worker_node")
        self.get_logger().info("Worker node started ")
        self.signals = signals

        self.actual_state = "unknown"
        self.latest_latitude = 0.0
        self.latest_longitude = 0.0
        self.latest_imu_z = 0.0
        self.latest_battery_v = 0.0
        self.latest_left_motor_v = 0.0
        self.latest_right_motor_v = 0.0
        self.latest_battery_percent = 0.0
        self._last_gui_emit_sec = 0.0

        self.image_publishers = {
            topic: self.create_publisher(Image, topic, 10) for topic in self.IMAGE_TOPICS
        }
        self.pub_state = self.create_publisher(String, "rover/state", 10)
        self.sub_state = self.create_subscription(String, "rover/state", self.state_callback, 10)
        self.sub_gps = self.create_subscription(NavSatFix, "rover/gps", self.gps_callback, 10)
        self.sub_imu = self.create_subscription(Imu, "rover/imu", self.imu_callback, 10)
        self.sub_status = self.create_subscription(Float32MultiArray, "rover/status", self.status_callback, 10)
        self.sub_front_camera = self.create_subscription(Image, "rover/camera_front_raw", self.front_camera_callback, 10)
        self.sub_rear_camera = self.create_subscription(Image, "rover/camera_rear_raw", self.rear_camera_callback, 10)
        
        #########testttt######
        self.sub_video_stream = self.create_subscription(Image, "video_stream", self.video_stream_callback, 10)
        #####

    @staticmethod
    def _copy_image(msg: Image, stamp, frame_id: str) -> Image:
        out = Image()
        out.header.stamp = stamp
        out.header.frame_id = frame_id
        out.height = msg.height
        out.width = msg.width
        out.encoding = msg.encoding
        out.is_bigendian = msg.is_bigendian
        out.step = msg.step
        out.data = list(msg.data)
        return out

    def front_camera_callback(self, msg: Image) -> None:
        stamp = self.get_clock().now().to_msg()
        
        self.pub_state.publish(String(data=self.actual_state))

        self.image_publishers["rover/camera/front"].publish(self._copy_image(msg, stamp, "front"))
        self.image_publishers["rover/debug/face"].publish(self._copy_image(msg, stamp, "face"))

        self.push_telemetry_to_gui()

    def rear_camera_callback(self, msg: Image) -> None:
        stamp = self.get_clock().now().to_msg()

        self.image_publishers["rover/camera/rear"].publish(self._copy_image(msg, stamp, "rear"))
       # self.image_publishers["rover/debug/lane_bev"].publish(self._copy_image(msg, stamp, "lane_bev"))
        self.image_publishers["rover/debug/lane_trace"].publish(self._copy_image(msg, stamp, "lane_trace"))
        self.push_telemetry_to_gui()

    ###############testttt######
    def video_stream_callback(self, msg: Image) -> None:
        stamp = self.get_clock().now().to_msg()
        self.image_publishers["rover/debug/lane_bev"].publish(self._copy_image(msg, stamp, "lane_bev"))
        self._latest_lane_bev_msg = msg

        self.push_telemetry_to_gui()
    ###################################

    def state_callback(self, msg: String) -> None:
        self.actual_state = msg.data
        self.push_telemetry_to_gui()

    def gps_callback(self, msg: NavSatFix) -> None:
        self.latest_latitude = msg.latitude
        self.latest_longitude = msg.longitude
        self.push_telemetry_to_gui()

    def imu_callback(self, msg: Imu) -> None:
        self.latest_imu_z = msg.linear_acceleration.z
        self.push_telemetry_to_gui()

    def status_callback(self, msg: Float32MultiArray) -> None: ####
        if len(msg.data) < 4:
            self.get_logger().warn(
                f"rover/status expected 4 values, got {len(msg.data)}"
            )
            return

        self.latest_battery_v = msg.data[0]
        self.latest_left_motor_v = msg.data[1]
        self.latest_right_motor_v = msg.data[2]
        self.latest_battery_percent = msg.data[3]
        self.push_telemetry_to_gui()

    def push_telemetry_to_gui(self) -> None: #lw a2al mn 0.1 my3mlsh 7aga
            now_sec = self.get_clock().now().nanoseconds / 1e9
            if now_sec - self._last_gui_emit_sec < self.GUI_EMIT_INTERVAL_SEC:
                return

            self._last_gui_emit_sec = now_sec
            self.signals.telemetry_received.emit(
                {
                    "status_state": self.actual_state,
                    "latitude": self.latest_latitude,
                    "longitude": self.latest_longitude,
                    "battery_voltage": self.latest_battery_v,
                    "left_motor_voltage": self.latest_left_motor_v,
                    "right_motor_voltage": self.latest_right_motor_v,
                    "battery_percent": self.latest_battery_percent,
                    "imu_accel_z": self.latest_imu_z,
                ####testttt######
                    "lane_bev_image": getattr(self, '_latest_lane_bev_msg', None),
                }
            )


class ROS2RoverWorker(QThread):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.signals = RoverSignals()
        self._executor: SingleThreadedExecutor | None = None
        self._node: WorkerNode | None = None

    def run(self) -> None:
        if not rclpy.ok():
            rclpy.init()

        self._node = WorkerNode(self.signals)
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)

        try:
            self._executor.spin()
        except Exception as exc:
            print(f"ROS2 thread exception: {exc}")
        finally:
            if self._executor is not None and self._node is not None:
                self._executor.remove_node(self._node)
            if self._node is not None:
                self._node.destroy_node()
                self._node = None
            self._executor = None
            if rclpy.ok():
                rclpy.shutdown()

    def stop(self, timeout_ms: int = 3000) -> None:
        if self._executor is not None:
            self._executor.shutdown()

        if not self.wait(timeout_ms):
            print("Warning: ROS2 worker thread did not stop in time.")
