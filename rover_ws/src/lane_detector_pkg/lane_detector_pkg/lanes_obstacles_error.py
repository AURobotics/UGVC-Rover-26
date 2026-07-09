import cv2
import rclpy 
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Int32,Bool
import os 
import numpy as np
from ultralytics import YOLO 
from ament_index_python.packages import get_package_share_directory
from lane_detector_pkg.lane_classic import RoadFeatureDetector
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy


Camera_topic = "camera/image/raw" #SUBSCRIBE
Lane_error_topic = "lane/error" #PUBLISHER
obstacle_error_topic = "obstacle/error" #PUBLISHER
obstacle_detected_topic = "obstacle/detected" #PUBLISHER

class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.bridge = CvBridge()

        self.K = np.array([
        [1000, 0, 960],
        [0, 1000, 540],
        [0, 0, 1]
        ], dtype=np.float64)
        self.camera_height = 1.2
        self.pitch_deg = -30
        self.yaw_deg = 0 
        self.roll_deg = 0
        self.lane_detector = None

        self.prev_left_x = None
        self.prev_right_x = None
        self.prev_lane_error = 0 

        package_share_dir = get_package_share_directory('lane_detector_pkg')
        model_path_obstacle = os.path.join(package_share_dir,'models','ModelForObstacle.pt')
        self.model_obstacle = YOLO(model_path_obstacle)

        self.camera_subscriber = self.create_subscription(
            Image,
            Camera_topic,
            self.camera_callback,
            qos_profile
        )
        self.lane_error_publisher = self.create_publisher(
            Int32,
            Lane_error_topic,
            qos_profile
        )
        self.obstacle_error_publisher= self.create_publisher(
            Int32,
            obstacle_error_topic,
            qos_profile
        )
        self.obstacle_detected_publisher = self.create_publisher(
            Bool,
            obstacle_detected_topic,
            qos_profile
        )

    
    def camera_callback(self,msg):
        try :
            frame = self.bridge.imgmsg_to_cv2(msg,desired_encoding = 'bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed To Convert Image as {e}')
            return

        if self.lane_detector is None :
            height, width = frame.shape[:2]
            self.lane_detector = RoadFeatureDetector(
            K = self.K,
            camera_height = self.camera_height,
            pitch_deg = self.pitch_deg,
            yaw_deg = self.yaw_deg,
            roll_deg = self.roll_deg,
            image_size = (width,height)
        )
        
        x_left , x_right , lane_error = self.get_lane_data(frame)
        
        if x_left is not None :
            self.prev_left_x = x_left
        else :
            x_left = self.prev_left_x

             
        if x_right is not None :
            self.prev_right_x = x_right
        else :
            x_right = self.prev_right_x    
                
        if x_left is not None and x_right is not None:
            lane_center = (x_left+x_right)//2
            image_center = frame.shape[1] // 2
            lane_error = lane_center - image_center
            self.prev_lane_error = lane_error
        else :
            lane_error = self.prev_lane_error    

        lane_error_msg = Int32()
        lane_error_msg.data = lane_error
        self.lane_error_publisher.publish(lane_error_msg)

        self.detect_obstacles(frame,x_left,x_right)

    def get_lane_data(self,frame):
        edges,_ = self.lane_detector.detect_edges(frame)
        lines = self.lane_detector.detect_lines(edges)
        left_fit,right_fit = self.lane_detector._fit_left_right_lanes(lines)
        look_ahead_y = int(frame.shape[0] * 0.7)

        x_left = None
        x_right = None
        if left_fit is not None:
            m_left , b_left = left_fit
            x_left = int(m_left * look_ahead_y + b_left)
        if right_fit is not None:    
            m_right, b_right = right_fit
            x_right = int (m_right * look_ahead_y + b_right)

        

        if x_left is not None and x_right is not None:
            lane_center = (x_left + x_right) // 2
            image_center = frame.shape[1] // 2 
            lane_error = lane_center - image_center
        else :
            lane_error = None       

        return x_left , x_right ,lane_error

    def detect_obstacles(self,frame,x_left,x_right):
        results_obstacles = self.model_obstacle(frame , conf = 0.3)[0]
        obstacles = [] 

        for box in results_obstacles.boxes:
            x1 ,y1 ,x2 ,y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            if confidence < 0.3 : 
                continue    
            center_x = (x1+x2) // 2
            center_y = (y1+y2) // 2  
            bottom_x = (x1 + x2) // 2
            bottom_y = y2 
            area_box = (x2-x1)*(y2-y1)
            obstacles.append({
                "x1" : x1,
                "x2" : x2,
                "y1" : y1,
                "y2" : y2,
                "area" : area_box,
                "center_x" : center_x,
                "center_y" : center_y,
                "bottom_x" : bottom_x,
                "bottom_y" : bottom_y,
                "conf" : confidence,
            })
        if x_left is None or x_right is None:
            return 
        lane_obstacles = []
        for obstacle in obstacles :
            bottom_x = obstacle["bottom_x"]
            if x_left <= bottom_x <= x_right : 
                lane_obstacles.append(obstacle)

        lane_obstacles.sort(key=lambda obstacle : obstacle["x1"])
        gaps = []
        if len(lane_obstacles) > 0 :
            gaps.append({
                "start" : x_left,
                "end" : lane_obstacles[0]["x1"]
            })
        for i in range (len(lane_obstacles)-1):
            gaps.append({
                "start" : lane_obstacles[i]["x2"],
                "end" : lane_obstacles[i+1]["x1"]
            })    
        if len(lane_obstacles) > 0 :
            gaps.append({
                "start" : lane_obstacles[-1]["x2"],
                "end" : x_right
            })    
        detected_msg = Bool()
        if len(lane_obstacles) == 0:
            detected_msg.data = False
        elif len(lane_obstacles) > 0:
            detected_msg.data = True
        self.obstacle_detected_publisher.publish(detected_msg)    

        if len(lane_obstacles) > 0 :
            for gap in gaps : 
                gap["width"] = gap["end"] - gap["start"]
            best_gap = max(gaps,key = lambda gap : gap["width"])
            target_center = (best_gap["start"] + best_gap["end"]) // 2 
            lane_center = (x_right+x_left) // 2
            obstacle_error = target_center - lane_center
 
            error_msg = Int32()
            error_msg.data = obstacle_error
            self.obstacle_error_publisher.publish(error_msg)   

            
def main(args = None):
    rclpy.init(args = args)
    node = ObstacleDetector()
    try :
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

