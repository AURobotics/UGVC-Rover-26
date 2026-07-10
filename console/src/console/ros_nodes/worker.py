import traceback
import threading
from PySide6.QtCore import QObject, QThread, Signal, Slot
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import CompressedImage, Imu
from std_msgs.msg import Float32MultiArray, String
from std_srvs.srv import SetBool
from nav_msgs.msg import Odometry
import tf_transformations
from geometry_msgs.msg import Twist
from rover_interfaces.msg import RoverStatus
from console.ros_nodes.joystick_node import JoystickNode
import math

class RoverSignals(QObject):
    telemetry_received = Signal(dict)
    rear_received = Signal(CompressedImage)
    front_received = Signal(CompressedImage)
    face_received = Signal(CompressedImage)
    lane_received = Signal(CompressedImage)
    video_received = Signal(CompressedImage)

class WorkerNode(Node):
    GUI_EMIT_INTERVAL_SEC = 0.1

    def __init__(self, signals: RoverSignals):
        super().__init__("worker_node")
        self.get_logger().info("Worker node started")
        self.signals = signals

        self.latest_latitude        = 0.0
        self.latest_longitude       = 0.0
        self.latest_bearing         = 0.0
        self.latest_linear_vel      = 0.0

        self.latest_battery_1       = 0.0
        self.latest_battery_2       = 0.0

        self.latest_motor_fl         = 0.0
        self.latest_motor_fr         = 0.0
        self.latest_motor_bl         = 0.0
        self.latest_motor_br         = 0.0

        self.sub_imu    = self.create_subscription(Imu,                "/imu/data",    self.imu_callback,    10)
        self.sub_vel    = self.create_subscription(Twist,              "/cmd_vel",     self.vel_callback,    10)
        self.sub_odom   = self.create_subscription(Odometry,           "/odom/global", self.odom_callback,   10)
        self.sub_status = self.create_subscription(RoverStatus,        "/rover/status",self.status_callback, 10)
    
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.sub_front = self.create_subscription(CompressedImage, "/camera1/image_raw",   self.front_raw_callback,   qos_profile)
        self.sub_rear  = self.create_subscription(CompressedImage, "/camera2/image_raw",    self.rear_raw_callback,    qos_profile)
       # self.sub_face  = self.create_subscription(CompressedImage, "rover/camera/face_detect", self.face_detect_callback, qos_profile)
       # self.sub_lane  = self.create_subscription(CompressedImage, "rover/camera/lane_detect", self.lane_detect_callback, qos_profile)
       # self.sub_video = self.create_subscription(CompressedImage, "video_stream", self.video_stream_callback, qos_profile)

        self.toggle_client = self.create_client(SetBool, '/manual_toggle')
        self.gui_timer = self.create_timer(self.GUI_EMIT_INTERVAL_SEC, self.push_telemetry_to_gui)

    #def video_stream_callback(self, msg: CompressedImage) -> None:
    #    self.signals.video_received.emit(msg)

   # def face_detect_callback(self, msg: CompressedImage) -> None:
   #     self.signals.face_received.emit(msg)
#
   # def lane_detect_callback(self, msg: CompressedImage) -> None:
   #     self.signals.lane_received.emit(msg)


    def front_raw_callback(self, msg: CompressedImage) -> None:
        self.signals.front_received.emit(msg)

    def rear_raw_callback(self, msg: CompressedImage) -> None:
        self.signals.rear_received.emit(msg)

    def odom_callback(self, msg: Odometry) -> None:
        self.latest_latitude  = msg.pose.pose.position.x
        self.latest_longitude = msg.pose.pose.position.y

    def imu_callback(self, msg: Imu) -> None:
        q = msg.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw_rad = math.atan2(siny_cosp, cosy_cosp)
        yaw_deg = math.degrees(yaw_rad)

        if yaw_deg < 0:
            yaw_deg += 360.0
        self.latest_bearing = yaw_deg 

    def vel_callback(self, msg: Twist) -> None:
        self.latest_linear_vel = msg.linear.x

    def status_callback(self, msg: RoverStatus) -> None:
        self.latest_battery_1 = msg.battery_voltage_1
        self.latest_battery_2 = msg.battery_voltage_2

        self.latest_motor_fl = msg.motor_current_fl
        self.latest_motor_fr = msg.motor_current_fr
        self.latest_motor_bl = msg.motor_current_bl
        self.latest_motor_br = msg.motor_current_br
        
    def auto_switch(self, is_auto: bool):
        if self.toggle_client.service_is_ready():
            req = SetBool.Request()
            req.data = not is_auto 
            
            mode_name = "Autonomous" if is_auto else "Manual"
            self.get_logger().info(f"Requesting switch to {mode_name} mode...")
            
            self.toggle_client.call_async(req)
        else:
            self.get_logger().warn("Waiting for '/manual_toggle' service...")

    def push_telemetry_to_gui(self) -> None:
        self.signals.telemetry_received.emit(
            {
                "latitude":            self.latest_latitude,
                "longitude":           self.latest_longitude,
                "bearing":             self.latest_bearing,
                "linear_vel":          self.latest_linear_vel,

                "battery_1":           self.latest_battery_1,
                "battery_2":           self.latest_battery_2,
                "motor_fl":            self.latest_motor_fl,
                "motor_fr":            self.latest_motor_fr,
                "motor_bl":            self.latest_motor_bl,
                "motor_br":            self.latest_motor_br,
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

    @Slot(bool)
    def auto_switch(self, is_auto: bool):
        if self._node is not None:
            self._node.auto_switch(is_auto)

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
