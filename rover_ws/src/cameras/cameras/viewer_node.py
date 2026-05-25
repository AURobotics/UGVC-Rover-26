import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy


class Viewer(Node):
    def __init__(self):
        super().__init__('video_viewer')
        self.bridge = CvBridge()

        image_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
            )
        
        self.create_subscription(Image, '/camera1/image_raw', self.camera1, image_qos)
        self.create_subscription(Image, '/camera2/image_raw', self.camera2, image_qos)
        
        self.get_logger().info('Viewer initialized with 2 windows')

    def camera1(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            cv2.imshow('Camera 1 Feed', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Camera 1 error: {e}')

    def camera2(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            cv2.imshow('Camera 2 Feed', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Camera 2 error: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = Viewer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()