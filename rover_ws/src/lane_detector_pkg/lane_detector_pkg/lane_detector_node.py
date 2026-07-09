import os
import rclpy 
from rclpy.node import Node
from std_msgs.msg import Int32
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy

Lane_error_topic = "lane/error"
lane_left_topic = "lane/left_x"
lane_right_topic = "lane/right_x"
Camera_topic = "camera/image/raw"
lane_target_topic = "lane/target_x"

class LaneDetector(Node) : 
    def __init__(self) :
        super().__init__('lane_detector')

        self.error_publisher = self.create_publisher(Int32,Lane_error_topic,10)
        self.get_logger().info('Lane Detector Node Started.')

        self.left_publisher = self.create_publisher(Int32,lane_left_topic,10)
        self.right_publisher = self.create_publisher(Int32,lane_right_topic,10)


        package_share_dir = get_package_share_directory('lane_detector_pkg')

        model_path_Lanes = os.path.join(package_share_dir,'models','ModelForLanes.pt')
        self.get_logger().info(f'Loading YOLO Model from : {model_path_Lanes}')
        self.model_Lanes = YOLO(model_path_Lanes)

        self.target_publisher = self.create_publisher(Int32,lane_target_topic,10)
        
        
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.subscription = self.create_subscription(
        Image,
        Camera_topic,
        self.camera_callback,
        qos_profile
        )       
        
        self.bridge = CvBridge()
        
        self.prev_center = None          
        self.prev_lane_width = 300       
        self.alpha = 0.7                 
        self.last_known_center = None
        self.bias = 100
        self.last_right_x = None
        self.last_left_x = None

    def camera_callback(self,msg):
        try : 
            frame = self.bridge.imgmsg_to_cv2(msg,desired_encoding = 'bgr8')
        except Exception as e:
            self.get_logger().error(f"Failed To Convert Image : {e}")
            return 
        image_height, image_width, _ = frame.shape
        X_target = image_width // 2
        look_ahead_Y = int(0.75 * image_height)

        results_lane= self.model_Lanes(frame ,conf = 0.25)[0]

        x_left_intersection = []
        x_right_intersection = []    
        

        for box in results_lane.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            if confidence < 0.25:        
                continue

            if not (y2 >= look_ahead_Y >= y1):
                continue

            if (y2 - y1) == 0:
                continue
            intersection_x = int(x1 + (look_ahead_Y - y1) * (x2 - x1) / (y2 - y1))

    
            if intersection_x > X_target:
                x_right_intersection.append(intersection_x)
            elif intersection_x < X_target:
                x_left_intersection.append(intersection_x)
    

        x_left = int(np.mean(x_left_intersection)) if x_left_intersection else None
        x_right = int(np.mean(x_right_intersection)) if x_right_intersection else None
        
        left_detected = x_left is not None
        right_detected = x_right is not None

        if x_left is not None : 
            self.last_left_x = x_left 
        else :
            x_left = self.last_left_x
        if x_right is not None :
            self.last_right_x = x_right
        else :
            x_right = self.last_right_x

        if x_left is not None :
            message_left = Int32()
            message_left.data = x_left
            self.left_publisher.publish(message_left)
        if x_right is not None : 
            message_right = Int32()
            message_right.data = x_right
            self.right_publisher.publish(message_right)

        if x_left is not None and x_right is not None:
            current_center = (x_left + x_right) // 2
        
            self.prev_lane_width = x_right - x_left
            self.last_known_center = current_center

        elif x_left is not None:   
            lane_width = self.prev_lane_width
            current_center = x_left + lane_width // 2
            self.last_known_center = current_center

        elif x_right is not None:  
            lane_width = self.prev_lane_width
            current_center = x_right - lane_width // 2
            self.last_known_center = current_center

        else:  
            if self.last_known_center is None:
                return
            else:
                current_center = self.last_known_center
        if self.prev_center is None:
            filtered_center = current_center
        else:
            filtered_center = int(self.alpha * current_center + (1 - self.alpha) * self.prev_center)
        self.prev_center = filtered_center

    
        error_pixels = filtered_center - X_target

        if left_detected and not right_detected :
            error_pixels += self.bias
        elif right_detected  and not left_detected :
            error_pixels -= self.bias

    
        msg = Int32()
        msg.data = error_pixels
        self.error_publisher.publish(msg)

        target_msg = Int32()
        target_msg.data = filtered_center
        self.target_publisher.publish(target_msg)
    
        

def main(args = None):
    rclpy.init(args = args)
    node = LaneDetector()
    try : 
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown() 

if __name__ == '__main__':
    main()                     





    

   

    
    
