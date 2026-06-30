import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy


class Viewer(Node):
    def __init__(self):
        super().__init__('video_viewer')
        self.bridge = CvBridge()

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.create_subscription(CompressedImage, '/camera1/image_raw', self.camera1, qos_profile)
        self.create_subscription(CompressedImage, '/camera2/image_raw', self.camera2, qos_profile)
        
        self.get_logger().info('Viewer initialized with 2 windows')

    def camera1(self, msg):
        try:
            frame = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='passthrough')
            cv2.imshow('Camera 1 Feed', frame)
            cv2.waitKey(1) # for testing, not effecient
        except Exception as e:
            self.get_logger().error(f'Camera 1 error: {e}')

    def camera2(self, msg):
        try:
            frame = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='passthrough')
            cv2.imshow('Camera 2 Feed', frame)
            cv2.waitKey(1) # for testing, not effecient
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