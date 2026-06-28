## Using Ready Vedio To Test 
#!/usr/bin/env python3
import os
import rclpy 
from rclpy.node import Node
from std_msgs.msg import Int32
import cv2
import numpy as np
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory

class LaneDetector(Node) : 
    def __init__(self) :
        super().__init__('lane_detector')

        self.publisher_ = self.create_publisher(Int32,'lane/error',10)
        self.get_logger().info('Lane Detector Node Started.')

        package_share_dir = get_package_share_directory('lane_detector_pkg')
        model_path = os.path.join(package_share_dir,'models','best.pt')
        vedio_path = os.path.join(package_share_dir,'videos','test3.mp4')

        self.get_logger().info(f'Loading YOLO Model from : {model_path}')
        self.model = YOLO(model_path)

        self.get_logger().info(f'Loading video from : {vedio_path}')
        self.cap = cv2.VideoCapture(vedio_path)

        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open video at: {vedio_path}')
            raise RuntimeError(f"Could not open video file at {vedio_path}")

        self.prev_center = None          
        self.prev_lane_width = 300       
        self.alpha = 0.7                 
        self.last_known_center = None
        self.bias = 100

        cv2.namedWindow('lane', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('lane', 800, 600)
        
        self.timer = self.create_timer(0.033,self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES,0)
            return
        image_height, image_width, _ = frame.shape
        X_target = image_width // 2
        look_ahead_Y = int(0.75 * image_height)

        results = self.model(frame)[0]
        frame = results.plot(conf=True)

        x_left_intersection = []
        x_right_intersection = []    
        

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            if confidence < 0.3:        
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
                cv2.putText(frame, "ERROR: No lanes detected!", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.imshow("lane", frame)
                cv2.waitKey(1)
                return
                
            else:
                current_center = self.last_known_center

    
        if self.prev_center is None:
            filtered_center = current_center
        else:
            filtered_center = int(self.alpha * current_center + (1 - self.alpha) * self.prev_center)
        self.prev_center = filtered_center

    
        error_pixels = filtered_center - X_target

        if x_left is not None and x_right is None:
            error_pixels += self.bias
        elif x_right is not None and x_left is None:
            error_pixels -= self.bias
        max_error = image_width // 2
        error_percent = int((error_pixels / max_error) * 100)

        if error_percent > 0:
            direction = "Right >>"
        elif error_percent < 0:
            direction = "Left <<"
        else:
            direction = "Center .."

        direction = f"Deviation : [{direction}] {abs(error_percent)}%"
        steering = f"Steering Value : {error_percent:+d}" 

        text_start_x = int(image_width * 0.55)  
    
    
        cv2.putText(frame, direction, (text_start_x, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(frame, steering, (text_start_x, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    
        msg = Int32()
        msg.data = error_percent
        self.publisher_.publish(msg)
    
        cv2.imshow('lane', frame)
        cv2.waitKey(1) 

def main(args = None):
    rclpy.init(args = args)
    node = LaneDetector()
    try : 
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown() 

if __name__ == '__main__':
    main()