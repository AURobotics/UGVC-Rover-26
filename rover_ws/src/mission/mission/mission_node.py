import sys
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from enum import Enum
from nav_msgs.msg import Odometry
from std_srvs.srv import SetBool
from std_msgs.msg import UInt8

WAYPOINT_ERROR = 1.25 # 1.5 allowed error in meters for reaching a waypoint (1.25 for safety)
WAYPOINT_TIMEOUT = 60 # 60 seconds allowed to reach a waypoint before timing out and returning to manual control
WAYPOINT2_TIMEOUT = 44 # 45 seconds allowed for face recognition to complete before timing out and returning to waypoint navigation

# Topics
LOCALIZATION_TOPIC = '/odom/global'
FACE_RECOGNITION_SERVICE = '/face_recognition/start'
MANUAL_TOGGLE_TOPIC = '/manual_toggle'
STATE_TOPIC = '/mission/active_state'

class State(Enum):
    MANUAL = 0 # Manual control mode
    AUTO_LANES = 1 # Autonomous lane following mode
    AUTO_WAYPOINTS = 2 # Autonomous waypoint navigation mode
    AUTO_WAYPOINT2 = 3 # Face recognition mode

class Mode(Enum):
    MANUAL = 0
    AUTO = 1

class MissionNode(Node):
    def __init__(self):
        super().__init__("mission_node")

        # 1. Initialize all tracking variables to prevent AttributeError race conditions
        self.position = None
        self.orientation = None
        self.linear_vel = None
        
        self.waypoint1_time = None
        self.waypoint2_time = None
        self.waypoint3_time = None

        self.waypoint2_done = False # waypoint2 completion flag

        self.state_topic_publisher = self.create_publisher(UInt8, STATE_TOPIC, 10)
        
        # Instantiate clients in constructor
        self.face_recognition_client = self.create_client(SetBool, FACE_RECOGNITION_SERVICE)

        self._declare_fetch_variables()

        self.state = State.MANUAL # Initial state is manual control for all modes
        
        if self.mode == Mode.AUTO:
            self.manual_toggle_server = self.create_service(
                SetBool,
                MANUAL_TOGGLE_TOPIC,
                self.manual_toggle_callback
            ) # Service is only used in auto to switch to and from manual

        self.position_subscriber = self.create_subscription(
            Odometry,
            LOCALIZATION_TOPIC,
            self.odom_callback,
            10
        )

        self.create_timer(0.05, self._control_loop)

    def _control_loop(self):
        if self.state == State.MANUAL:
            self.state_topic_publisher.publish(UInt8(data=State.MANUAL.value))

        elif self.state == State.AUTO_LANES:
            if self.is_at_waypoint(1):
                self.state = State.AUTO_WAYPOINTS
                self.waypoint1_time = self.get_clock().now()
                self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINTS.value))
                return
            
            self.state_topic_publisher.publish(UInt8(data=State.AUTO_LANES.value))

        elif self.state == State.AUTO_WAYPOINTS:
            is_timed_out1 = False
            if self.waypoint1_time is not None: 
                is_timed_out1 = (self.get_clock().now() - self.waypoint1_time) >= Duration(seconds=WAYPOINT_TIMEOUT)
            
            is_timed_out3 = False
            if self.waypoint3_time is not None:
                is_timed_out3 = (self.get_clock().now() - self.waypoint3_time) >= Duration(seconds=WAYPOINT_TIMEOUT * 2) 

            if (self.is_at_waypoint(2) or is_timed_out1) and not self.waypoint2_done:
                self.state = State.AUTO_WAYPOINT2
                self.waypoint2_time = self.get_clock().now()
                self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINT2.value))
                self.start_waypoint2()
                return
            elif self.is_at_waypoint(3) or is_timed_out3:
                self.state = State.AUTO_LANES
            
            self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINTS.value))
        
        elif self.state == State.AUTO_WAYPOINT2:
            is_timed_out2 = None
            if self.waypoint2_time is not None:
                is_timed_out2 = (self.get_clock().now() - self.waypoint2_time) >= Duration(seconds=WAYPOINT2_TIMEOUT)
            
            if is_timed_out2:
                self.call_face_recognition_service(False, "Stopping face recognition after 45 seconds")
                self.waypoint2_done = True
                self.state = State.AUTO_WAYPOINTS
                self.waypoint3_time = self.get_clock().now()
                return
            #if WAYPOINT2 is completed: (node for servo movement to center the face isn't written yet)
            # I will wait to take feedback from this node since it is the one that will be firing the laser
            # or the node that fires the laser
            #self.call_face_recognition_service(False, "Stopping face recognition after completion")
            #self.state=State.AUTO_WAYPOINTS

            self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINT2.value))

# ===== helper functions ================================================================================

    def _declare_fetch_variables(self):
        self.declare_parameter('mode', 0)  # 0: manual, 1: auto
        mode_value = self.get_parameter('mode').get_parameter_value().integer_value
        
        # in case of manual mode, State = MANUAL and no switching
        if mode_value not in [0, 1]:
            self.get_logger().error("Invalid mode parameter. Must be 0 (manual) or 1 (auto).")
            sys.exit(1)
        elif mode_value == 0:
            self.mode = Mode.MANUAL
            return # if manual mode, no need to declare other variables
        self.mode = Mode.AUTO

        # waypoint coordinates (only used in auto mode)
        self.declare_parameter('waypoint1.x', 0.0)
        self.declare_parameter('waypoint1.y', 0.0)
        self.declare_parameter('waypoint2.x', 1.0)
        self.declare_parameter('waypoint2.y', 1.0)
        self.declare_parameter('waypoint3.x', 2.0)
        self.declare_parameter('waypoint3.y', 2.0)
        
        self.waypoints = [
            (self.get_parameter('waypoint1.x').value, self.get_parameter('waypoint1.y').value),
            (self.get_parameter('waypoint2.x').value, self.get_parameter('waypoint2.y').value),
            (self.get_parameter('waypoint3.x').value, self.get_parameter('waypoint3.y').value)
        ]

    def odom_callback(self, msg: Odometry):
        self.position = msg.pose.pose.position
        self.orientation = msg.pose.pose.orientation
        self.linear_vel = msg.twist.twist.linear

    def is_at_waypoint(self, waypoint_number):
        if self.position is None:
            return False
        
        distance = ((self.position.x - self.waypoints[waypoint_number-1][0]) ** 2 + 
                    (self.position.y - self.waypoints[waypoint_number-1][1]) ** 2) ** 0.5
        return distance <= WAYPOINT_ERROR
    
    # WAYPOINT 2: Face recognition Functions
    def start_waypoint2(self):        
        self.call_face_recognition_service(True, "Starting face recognition for waypoint 2")

    def call_face_recognition_service(self, state: bool, reason: str = ""):
        if not self.face_recognition_client.service_is_ready():
            self.get_logger().error("[SESSION] Face recognition service not available")
            return

        request = SetBool.Request()
        request.data = state
        future = self.face_recognition_client.call_async(request)
        future.add_done_callback(
            lambda f: self.face_recognition_client_callback(f, reason)
        )

    def face_recognition_client_callback(self, future, reason: str):
        try:
            response = future.result()
            tag = f" ({reason})" if reason else ""
            self.get_logger().info(f"Service response{tag}: {response.message}")
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    def manual_toggle_callback(self, request, response):
        if request.data:
            self.state = State.MANUAL
            response.success = True
            response.message = "Switched to manual control"
            self.get_logger().info("Switched to manual control")
        else:
            if self.state == State.MANUAL:
                self.state = State.AUTO_LANES
                response.success = True
                response.message = "Switched to autonomous lane following"
                self.get_logger().info("Switched to autonomous lane following")
            else:
                response.success = False
                response.message = "Already in autonomous mode"
                self.get_logger().info("Already in autonomous mode")
        return response

def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()