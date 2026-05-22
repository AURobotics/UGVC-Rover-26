import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class VideoStreamNode(Node):
    def __init__(self):
        super().__init__('video_stream_node')
        self.publisher_ = self.create_publisher(Image, 'video_stream', 10)
        self.bridge = CvBridge()
        self.cap = cv2.VideoCapture(0)
        cam_interval = 1 / 30
        self.timer = self.create_timer(cam_interval, self.publish_video_stream)

    def publish_video_stream(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.publisher_.publish(msg)
            self.get_logger().info('Published video frame.')
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