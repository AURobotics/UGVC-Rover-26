import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge
import cv2

class VideoStreamNode(Node):
    def __init__(self):
        super().__init__('video_stream_node')
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.publisher_ = self.create_publisher(CompressedImage, 'video_stream', qos_profile)
        self.bridge = CvBridge()
        self.cap = cv2.VideoCapture(0)
        cam_interval = 1 / 30
        self.timer = self.create_timer(cam_interval, self.publish_video_stream)

    def publish_video_stream(self):
        ret, frame = self.cap.read()
        if ret:
            success, compressed_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
            if success:
                msg = CompressedImage()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.format = 'jpeg'
                msg.data = compressed_frame.tobytes()
                self.publisher_.publish(msg)
                self.get_logger().info('Published video frame.')
            else:
                self.get_logger().warn('Failed to encode frame.')
        else:
            self.get_logger().warn('Failed to grab frame from camera.')

def main(args=None):
    rclpy.init(args=args)
    node = VideoStreamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()