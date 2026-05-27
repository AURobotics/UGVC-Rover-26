import cv2 
import numpy as np
from ultralytics import YOLO

model = YOLO("best.pt")

cap = cv2.VideoCapture("vedio5.mp4")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    image_height , image_width , _ = frame.shape # to get dim of frame
    X_target = image_width // 2 # to find target place for rover , // int devision

    look_ahead_Y = int(0.75 * image_height)  ## line intersect with left , right box 
    results = model(frame)[0] # run yolo model
    frame = results.plot(conf = True)
    x_left_intersection = []
    x_right_intersection = []

    for box in results.boxes : 
        x1 , y1 , x2 , y2 = map(int,box.xyxy[0])

        confidence = float(box.conf[0])
        if confidence < 0.25 :
            continue
        box_center_x = (x1 + x2) // 2   

        if y2 >= look_ahead_Y >= y1 : 
            if(y2-y1) != 0 :
                intersection_x = x1 + ((look_ahead_Y-y1)*(x2-x1))//(y2-y1) #linear interpolation 
            else :
                intersection_x = box_center_x
        else : intersection_x = box_center_x

        if box_center_x > X_target :
            x_right_intersection.append(intersection_x)
        elif box_center_x < X_target:
            x_left_intersection.append(intersection_x) 

    if x_left_intersection :
        x_left = int(np.mean(x_left_intersection)) 
    else : x_left = None    
    if x_right_intersection :
        x_right = int(np.mean(x_right_intersection))
    else : x_right = None    

    if x_left is not None and x_right is not None :
        current_center = (x_left + x_right) // 2
        error_pixels = current_center - X_target
        max_error = image_width // 2
        error_percent = int((error_pixels / max_error)*100)
        steering_error = error_percent

    
        if error_percent > 0:
            dev_char = "Right"
        elif error_percent < 0:
            dev_char = "Left"
        else:
            dev_char = "Center"
            
        direction = f"Deviation : [{dev_char}] {abs(error_percent)}%"
        steering = f"Steering Value : {steering_error:+d}" 

        box_x1 = int(image_width * 0.55)  
        box_y1 = 15                      
        box_x2 = int(image_width * 0.98)  
        box_y2 = 170                      
        
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (20, 20, 20), -1) 
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (100, 100, 100), 2)

        text_start_x = box_x1 + 15  
        
        cv2.putText(frame, direction, (text_start_x, box_y1 + 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        
        cv2.putText(frame, steering, (text_start_x, box_y1 + 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    else:

        cv2.putText(frame,"WARNING: Lanes Lost",(30, 50),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0, 0, 255),2)
        
    cv2.imshow("lane", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break
cap.release()
cv2.destroyAllWindows()
