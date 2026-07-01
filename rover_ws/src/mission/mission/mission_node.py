import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from enum import Enum,auto
from rover_interfaces.msg import RoverStatus, Speed, WheelVel # type: ignore
from nav_msgs.msg import Odometry
from std_srvs.srv import SetBool

WAYPOINT_ERROR = 1.25 # 1.5 allowed error in meters for reaching a waypoint (1.25 for safety)
WAYPOINT_TIMEOUT = 60 # 60 seconds allowed to reach a waypoint before timing out and returning to manual control

# Topics
LOCALIZATION_TOPIC = '/odometry/unfiltered'
FACE_RECOGNITION_SERVICE = '/face_recognition/start'

class State(Enum):
    MANUAL = auto() # Manual control mode
    AUTO_LANES = auto() # Autonomous lane following mode
    AUTO_WAYPOINTS = auto() # Autonomous waypoint navigation mode
    AUTO_WAYPOINT2 = auto() # Face recognition mode


class MissionNode(Node):
    def __init__(self):
        super().__init__("mission_node")

        self._declare_fetch_variables()

        if self.mode == 0:
            self.state = State.MANUAL
            self._initiate_manual()
        elif self.mode == 1:
            self.state = State.AUTO_LANES
            self._initiate_auto()

        self.position_subscriber = self.create_subscription(
            Odometry,
            LOCALIZATION_TOPIC,
            self.odom_callback,
            10
        )

        self.create_timer(0.05,self._control_loop)

    # main loop checking states
    def _control_loop(self):
        if self.state==State.MANUAL:
            pass

        elif self.state==State.AUTO_LANES:
            if self.is_at_waypoint(1):
                self.state=State.AUTO_WAYPOINTS
                self.waypoint1_time = self.get_clock().now()

        elif self.state==State.AUTO_WAYPOINTS:
            if self.waypoint1_time is not None: 
                is_timed_out1 = self.get_clock().now() - self.waypoint1_time >= Duration(seconds=WAYPOINT_TIMEOUT)
            else:
                is_timed_out1 = False
            if self.waypoint3_time is not None:
                is_timed_out3 = self.get_clock().now() - self.waypoint3_time >= Duration(seconds=WAYPOINT_TIMEOUT*2) 
            else:
                is_timed_out3 = False

            if self.is_at_waypoint(2) or is_timed_out1:
                self.state=State.AUTO_WAYPOINT2
                self.waypoint2_time = self.get_clock().now()
                self.start_waypoint2()
            elif self.is_at_waypoint(3) or is_timed_out3:
                self.state=State.AUTO_LANES

        elif self.state==State.AUTO_WAYPOINT2:
            is_timed_out2 = self.get_clock().now() - self.waypoint2_time >= Duration(seconds=44)
            if is_timed_out2:
                self.call_face_recognition_service(False, "Stopping face recognition after 45 seconds")
                self.state=State.AUTO_WAYPOINTS
                self.waypoint3_time = self.get_clock().now()
            #if WAYPOINT2 is completed: (node for servo movement to center the face isn't written yet)
            # I will wait to take feedback from this node since it is the one that will be firing the laser
            # or the node that fires the laser
            #self.call_face_recognition_service(False, "Stopping face recognition after completion")
            #self.state=State.AUTO_WAYPOINTS

# ===== helper functions ================================================================================

    def _declare_fetch_variables(self):
        # mode of operation:
        self.declare_parameter('mode', 0)  # 0: manual, 1: auto
        self.mode = self.get_parameter('mode').get_parameter_value().integer_value

        # waypoint coordinates (only used in auto mode)
        self.declare_parameter('waypoint1.x', 0.0)
        self.declare_parameter('waypoint1.y', 0.0)
        self.declare_parameter('waypoint2.x', 1.0)
        self.declare_parameter('waypoint2.y', 1.0)
        self.declare_parameter('waypoint3.x', 2.0)
        self.declare_parameter('waypoint3.y', 2.0)
        self.waypoints = [
            (
                self.get_parameter('waypoint1.x').value,
                self.get_parameter('waypoint1.y').value
            ),
            (
                self.get_parameter('waypoint2.x').value,
                self.get_parameter('waypoint2.y').value
            ),
            (
                self.get_parameter('waypoint3.x').value,
                self.get_parameter('waypoint3.y').value
            )
        ]

    def _initiate_manual(self):
        pass

    def _initiate_auto(self):
        pass

    def odom_callback(self, msg: Odometry):
        # 3. Access data from the incoming message structure
        self.position = msg.pose.pose.position
        self.orientation = msg.pose.pose.orientation
        self.linear_vel = msg.twist.twist.linear

    def is_at_waypoint(self, waypoint_number):
        if self.position is None:
            return False
        
        distance = ((self.position.x - self.waypoints[waypoint_number-1][0]) ** 2 + (self.position.y - self.waypoints[waypoint_number-1][1]) ** 2) ** 0.5
        return distance <= WAYPOINT_ERROR
    
    # WAYPOINT 2: Face recognition Functions

    def start_waypoint2(self):        
        self.face_recognition_client = self.create_client(SetBool, FACE_RECOGNITION_SERVICE)
        
        self.call_face_recognition_service(True, "Starting face recognition for waypoint 2")

    def call_face_recognition_service(self, state: bool, reason: str = ""):
        if not self.face_recognition_client.service_is_ready():
            print("[SESSION] Face recognition service not available", flush=True, file=sys.stdout)
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
            print(f"[SESSION] Service response{tag}: {response.message}", flush=True, file=sys.stdout)
        except Exception as e:
            print(f"[SESSION] Service call failed: {e}", flush=True, file=sys.stdout)

def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()

    

