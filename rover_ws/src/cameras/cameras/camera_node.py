import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
import cv2

class UsbCameraPublisher(Node):
    def __init__(self):
        super().__init__('usb_camera_publisher')

        # Parameters
        self.declare_parameter('device_index', 0)       # /dev/video0
        self.declare_parameter('publish_rate', 30.0)    # Hz
        self.declare_parameter('frame_id', 'camera')
        self.declare_parameter('topic', '/camera/image_raw')

        device_index = self.get_parameter('device_index').value
        rate         = self.get_parameter('publish_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        topic        = self.get_parameter('topic').value

        # QoS — Best Effort matches what camera drivers and subscribers expect
        camera_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, topic, camera_qos)

        # Open capture
        self.cap = cv2.VideoCapture(device_index)
        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open camera at index {device_index}')
            raise RuntimeError('Camera not available')

        self.get_logger().info(f'Camera opened at /dev/video{device_index}, publishing to {topic}')
        self.create_timer(1.0 / rate, self.timer_cb)

    def timer_cb(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('Failed to grab frame')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        self.pub.publish(msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = UsbCameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()