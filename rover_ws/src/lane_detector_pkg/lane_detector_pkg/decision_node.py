obstacle_error_topic = "obstacle/error" #subscriber
obstacle_detected_topic = "obstacle/detected" #subscriber
lane_error_topic = "lane/error" #subscriber
rover_error_topic = "rover/error" #publisher




import rclpy 
from rclpy.node import Node
from std_msgs.msg import Int32
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy


class RoverDetector(Node):
    def __init__(self):
        super().__init__('rover_detector')

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.error_obstacle_subscriber = self.create_subscription(Int32,obstacle_error_topic,self.obstacle_callback,qos_profile)

        self.error_lane_subscriber = self.create_subscription(Int32,lane_error_topic,self.lane_callback,qos_profile)

        self.detected_obstacle_subscriber = self.create_subscription(Bool,obstacle_detected_topic,self.detected_callback,qos_profile)

        self.rover_error_publisher = self.create_publisher(Int32,rover_error_topic,qos_profile)
        
        

        self.timer = self.create_timer(0.033, self.timer_callback)
        self.lane_error = 0
        self.obstacle_error = 0 
        self.obstacle_detected = False

        
       

    def lane_callback(self,msg):
        self.lane_error = msg.data
    def obstacle_callback(self,msg):
        self.obstacle_error = msg.data
    def detected_callback(self,msg):
        self.obstacle_detected = msg.data    
    def timer_callback(self):
        rover_msg = Int32()
        if self.obstacle_detected:
            rover_msg.data = self.obstacle_error
        else :
            rover_msg.data = self.lane_error
        self.rover_error_publisher.publish(rover_msg)
def main(args = None):
    rclpy.init(args = args)
    node = RoverDetector()
    try :
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
if __name__ == "__main__":
    main()                