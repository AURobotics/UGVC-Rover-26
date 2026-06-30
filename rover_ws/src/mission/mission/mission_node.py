import rclpy
from rclpy.node import Node
from enum import Enum,auto
from std_msgs.msg import String
# from rover_interfaces.msg import RoverStatus, Speed, WheelVel
from sensor_msgs.msg import Image, CompressedImage

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

        self.create_timer(0.05,self._control_loop)

    # main loop checking states
    def _control_loop(self):
        if self.state==State.MANUAL:
            pass
        elif self.state==State.AUTO_LANES:
            pass
        elif self.state==State.AUTO_WAYPOINTS:
            pass
        elif self.state==State.AUTO_WAYPOINT2:
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
        self.waypoint1 = (
            self.get_parameter('waypoint1.x').value,
            self.get_parameter('waypoint1.y').value
        )
        self.waypoint2 = (
            self.get_parameter('waypoint2.x').value,
            self.get_parameter('waypoint2.y').value
        )
        self.waypoint3 = (
            self.get_parameter('waypoint3.x').value,
            self.get_parameter('waypoint3.y').value
        )

    def _initiate_manual(self):
        pass

    def _initiate_auto(self):
        pass


    
def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()

    

