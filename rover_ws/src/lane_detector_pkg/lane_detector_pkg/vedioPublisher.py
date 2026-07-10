# use live vedio to test 

Camera_topic = "camera/image/raw" #publisher
rover_error_topic = "total/error" #subscriber


import os 
import cv2
import rclpy 
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from ament_index_python.packages import get_package_share_directory
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy



class CameraPublisher(Node):
    def __init__(self):
        super().__init__("vedioPublisher")

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.publisher = self.create_publisher(Image,Camera_topic,qos_profile)

        self.error_subscribtion = self.create_subscription(
            Float32,
            rover_error_topic,
            self.error_callback,
            qos_profile
        )

       

        self.rover_error = 0
        self.rover_target = None
        self.lane_target = None

        self.bridge = CvBridge()

        package_share_dir = get_package_share_directory("lane_detector_pkg")
        vedio_path = os.path.join(package_share_dir,"videos","test3.mp4")

        self.cap = cv2.VideoCapture(vedio_path)

        if not self.cap.isOpened() :
            self.get_logger().error(f"Can't open {vedio_path}")
            raise RuntimeError("failed to open the vedio")

        cv2.namedWindow("Rover Test", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Rover Test", 800, 600)    

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps  <= 0:
            fps = 30.0

        self.timer = self.create_timer(1.0 / fps,self.timer_callback)
    def error_callback(self,msg):
        self.rover_error = msg.data
 

    def timer_callback(self):
        ret , frame = self.cap.read()

        if not ret : 
            self.cap.set(cv2.CAP_PROP_POS_FRAMES,0)
            return

        msg = self.bridge.cv2_to_imgmsg(frame,encoding = 'bgr8')
        self.publisher.publish(msg) 

        if self.rover_error > 0:
            direction = "Right"
        elif self.rover_error < 0:
            direction = "Left"
        else:
            direction = "Center"

        cv2.putText(
    frame,
    f"Rover Error: {self.rover_error}",
    (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.8,
    (0, 255, 0),
    2
)

        cv2.putText(
    frame,
    f"Direction: {direction}",
    (20, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.8,
    (0, 255, 255),
    2
)

        if self.rover_target is not None:
            cv2.circle(
        frame,
        (self.rover_target, int(frame.shape[0] * 0.75)),
        8,
        (0, 0, 255),
        -1
    )

        look_ahead_y = int(frame.shape[0] * 0.75)

        if self.lane_target is not None:
            cv2.circle(
        frame,
        (self.lane_target, look_ahead_y),
        8,
        (255, 0, 0),   # أزرق
        -1
    )
        cv2.imshow("Rover Test", frame)
        cv2.waitKey(1)

def main(args = None):
    rclpy.init(args = args)
    node = CameraPublisher()
    try : 
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass 
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
