#! /usr/bin/env python3
import traceback
import threading
from PySide6.QtCore import QObject, QThread, Signal
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image, Imu, NavSatFix
from std_msgs.msg import Float32MultiArray, String
from console.ros_nodes.joystick_node import JoystickNode

class RoverSignals(QObject):
    telemetry_received = Signal(dict)

class WorkerNode(Node):
    GUI_EMIT_INTERVAL_SEC = 0.1

    def __init__(self, signals: RoverSignals):
        super().__init__("worker_node")
        self.get_logger().info("Worker node started")
        self.signals = signals

        self.actual_state           = "unknown"
        self.latest_latitude        = 0.0
        self.latest_longitude       = 0.0
        self.latest_imu_z           = 0.0
        self.latest_battery_v       = 0.0
        self.latest_left_motor_v    = 0.0
        self.latest_right_motor_v   = 0.0
        self.latest_battery_percent = 0.0

        self._latest_front_raw_msg   = None
        self._latest_rear_raw_msg    = None
        self._latest_face_detect_msg = None
        self._latest_lane_detect_msg = None

        self._front_updated = False
        self._rear_updated  = False
        self._face_updated  = False
        self._lane_updated  = False

        self.pub_state  = self.create_publisher(String, "rover/state", 10)
        self.sub_state  = self.create_subscription(String,             "rover/state",  self.state_callback,  10)
        self.sub_gps    = self.create_subscription(NavSatFix,          "rover/gps",    self.gps_callback,    10)
        self.sub_imu    = self.create_subscription(Imu,                "rover/imu",    self.imu_callback,    10)
        self.sub_status = self.create_subscription(Float32MultiArray,  "rover/status", self.status_callback, 10)

        self.sub_front = self.create_subscription(Image, "rover/camera/front_raw",   self.front_raw_callback,   1)
        self.sub_rear  = self.create_subscription(Image, "rover/camera/rear_raw",    self.rear_raw_callback,    1)
        self.sub_face  = self.create_subscription(Image, "rover/camera/face_detect", self.face_detect_callback, 1)
        self.sub_lane  = self.create_subscription(Image, "rover/camera/lane_detect", self.lane_detect_callback, 1)

        self.gui_timer = self.create_timer(self.GUI_EMIT_INTERVAL_SEC, self.push_telemetry_to_gui)

    def front_raw_callback(self, msg: Image) -> None:
        self._latest_front_raw_msg = msg
        self._front_updated = True

    def rear_raw_callback(self, msg: Image) -> None:
        self._latest_rear_raw_msg = msg
        self._rear_updated = True

    def face_detect_callback(self, msg: Image) -> None:
        self._latest_face_detect_msg = msg
        self._face_updated = True

    def lane_detect_callback(self, msg: Image) -> None:
        self._latest_lane_detect_msg = msg
        self._lane_updated = True

    def state_callback(self, msg: String) -> None:
        self.actual_state = msg.data

    def gps_callback(self, msg: NavSatFix) -> None:
        self.latest_latitude  = msg.latitude
        self.latest_longitude = msg.longitude

    def imu_callback(self, msg: Imu) -> None:
        self.latest_imu_z = msg.linear_acceleration.z

    def status_callback(self, msg: Float32MultiArray) -> None:
        if len(msg.data) < 4:
            self.get_logger().warn(f"rover/status expected 4 values, got {len(msg.data)}")
            return
        self.latest_battery_v       = msg.data[0]
        self.latest_left_motor_v    = msg.data[1]
        self.latest_right_motor_v   = msg.data[2]
        self.latest_battery_percent = msg.data[3]

    def push_telemetry_to_gui(self) -> None:
        front_img = self._latest_front_raw_msg   if self._front_updated else None
        rear_img  = self._latest_rear_raw_msg    if self._rear_updated  else None
        face_img  = self._latest_face_detect_msg if self._face_updated  else None
        lane_img  = self._latest_lane_detect_msg if self._lane_updated  else None

        self._front_updated = False
        self._rear_updated  = False
        self._face_updated  = False
        self._lane_updated  = False

        self.signals.telemetry_received.emit(
            {
                "status_state":        self.actual_state,
                "latitude":            self.latest_latitude,
                "longitude":           self.latest_longitude,
                "battery_voltage":     self.latest_battery_v,
                "left_motor_voltage":  self.latest_left_motor_v,
                "right_motor_voltage": self.latest_right_motor_v,
                "battery_percent":     self.latest_battery_percent,
                "imu_accel_z":         self.latest_imu_z,
                "front_raw_image":     front_img,
                "rear_raw_image":      rear_img,
                "face_detect_image":   face_img,
                "lane_detect_image":   lane_img,
            }
        )

class ROS2Worker(QThread):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.signals = RoverSignals()
        self._executor: SingleThreadedExecutor | None = None
        self._node: WorkerNode | None = None
        self._joystick_node: JoystickNode | None = None
        self._ready_event = threading.Event()

    def wait_until_ready(self, timeout_ms: int = 5000) -> None:
        """Block the calling thread until run() has finished node construction."""
        self._ready_event.wait(timeout=timeout_ms / 1000)

    def run(self) -> None:
        self._ready_event.clear()  # reset in case the thread is restarted
        rclpy.init()

        try:
            self._node = WorkerNode(self.signals)
        except Exception as exc:
            print(f"Failed to initialize WorkerNode: {exc}")
            traceback.print_exc()
            self._ready_event.set()
            rclpy.shutdown()
            return

        try:
            self._joystick_node = JoystickNode()
        except Exception as exc:
            # Non-fatal: rover can operate without joystick
            print(f"Warning: JoystickNode failed to initialize, continuing without it: {exc}")
            traceback.print_exc()
            self._joystick_node = None

        self._ready_event.set()  # unblock Mediator.wait_until_ready()

        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        if self._joystick_node is not None:
            self._executor.add_node(self._joystick_node)

        active_nodes = ["worker_node"] + (["joystick_node"] if self._joystick_node else [])
        print(f"ROS2 worker spinning (nodes: {', '.join(active_nodes)})")

        try:
            self._executor.spin()
        except Exception as exc:
            print(f"ROS2 thread exception: {exc}")
            traceback.print_exc()
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        print("ROS2 worker shutting down...")
        if self._executor is not None:
            if self._node is not None:
                self._executor.remove_node(self._node)
            if self._joystick_node is not None:
                self._executor.remove_node(self._joystick_node)

        if self._node is not None:
            self._node.destroy_node()
            self._node = None

        if self._joystick_node is not None:
            self._joystick_node.destroy_node()
            self._joystick_node = None

        self._executor = None

        if rclpy.ok():
            rclpy.shutdown()

    def stop(self, timeout_ms: int = 3000) -> None:
        if self._executor is not None:
            self._executor.shutdown()
        if not self.wait(timeout_ms):
            print("Warning: ROS2 worker thread did not stop in time.")