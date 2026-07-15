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
        
        # Create separate subscriptions with different callbacks
        self.create_subscription(Image, '/camera/image_raw', self.camera_cb, image_qos)
        self.create_subscription(Image, '/road_detector/debug/lane_mask', self.lane_mask_cb, image_qos)
        self.create_subscription(Image, '/road_detector/debug/bev_image', self.bev_cb, image_qos)
        
        self.get_logger().info('Viewer initialized with 3 windows')

    def camera_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            cv2.imshow('Camera Feed', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Camera error: {e}')

    def lane_mask_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            cv2.imshow('Lane Mask', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'Lane mask error: {e}')

    def bev_cb(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            cv2.imshow('BEV Image', frame)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f'BEV error: {e}')

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