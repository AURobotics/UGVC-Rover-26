import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from enum import Enum,auto
from rover_interfaces.msg import RoverStatus, Speed, WheelVel # type: ignore
from nav_msgs.msg import Odometry
from std_srvs.srv import SetBool

WAYPOINT_ERROR = 1.25 # 1.5 allowed error in meters for reaching a waypoint (1.25 for safety)

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
            '/odometry/unfiltered',
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
        elif self.state==State.AUTO_WAYPOINTS:
            if self.is_at_waypoint(2):
                self.state=State.AUTO_WAYPOINT2
                self.start_waypoint2()
            elif self.is_at_waypoint(3):
                self.state=State.AUTO_LANES
            pass
        elif self.state==State.AUTO_WAYPOINT2:
            if self._clock.now() - self.waypoint2_start_time >= Duration(seconds=44):
                self.state=State.AUTO_WAYPOINTS
            #if WAYPOINT2 is completed:
            #self.state=State.AUTO_WAYPOINTS
            pass

    # --- helper functions ---
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
    
    def start_waypoint2(self):
        self.waypoint2_start_time = self.get_clock().now()
        # Implement the logic to start waypoint 2
        pass

    
def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()

    

