import rclpy
from rclpy.node import Node
from enum import Enum,auto
from std_msgs.msg import String
# from rover_interfaces.msg import RoverStatus, Speed, WheelVel
from sensor_msgs.msg import Image, CompressedImage

class State(Enum):
    IDLE = auto() # specify mode of operation (manual or autonomous)
    MANUAL = auto() # Manual control mode
    AUTO_LANES = auto() # Autonomous lane following mode
    AUTO_WAYPOINTS = auto() # Autonomous waypoint navigation mode
    AUTO_WAYPOINT2 = auto() # Face recognition mode

class MissionNode(Node):
    def __init__(self):
        super().__init__("mission_node")

        # attributes
        self.state=State.IDLE

        self.create_timer(0.05,self._control_loop)

    def _control_loop(self):
        if self.state==State.MANUAL:
            pass
        elif self.state==State.AUTO_LANES:
            pass
        elif self.state==State.AUTO_WAYPOINTS:
            pass
        elif self.state==State.AUTO_WAYPOINT2:
            pass

    
def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()

    

