import cv2
import numpy as np
from cv2 import ximgproc

cap = cv2.VideoCapture("D:\\Software work\\rover 26\\test_lane.mp4")

def region_of_interest(frame):
    height = frame.shape[0]
    width = frame.shape[1]
    polygon = np.array([[
        (0, height),
        (width, height),
        (width // 2 + 150, height // 2),
        (width // 2 - 150, height // 2)
    ]], np.int32)

    mask = np.zeros_like(frame)
    cv2.fillPoly(mask, polygon, 255)

    return cv2.bitwise_and(frame, mask)

def detect_edges(frame):
    blur = cv2.GaussianBlur(frame, (5,5), 0)
    
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    
    lower_white = np.array([0,0,200])
    higher_white = np.array([180,50,255])
    
    # white segmentation
    mask = cv2.inRange(hsv, lower_white, higher_white)
    
    # remove small noise
    kernel = np.ones((5,5), np.uint8)
    
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # connect white regions
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # convert thick line to single-pixel line
    thin = ximgproc.thinning(mask)
    
    return thin

def detect_lines(edges):
     return cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=30)


def draw_lines(frame, lines):
     for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(frame, (x1,y1), (x2,y2), (0, 255, 0), 5)


while True:
    ret, frame = cap.read()

    if not cap.isOpened():
        print("Cannot open video file")
        break
    
    if not ret:
        cap = cv2.VideoCapture("test_lane.mp4")
        continue

    height = frame.shape[0]
    width = frame.shape[1]
    
    cropped_image = region_of_interest(frame)

    edges = detect_edges(frame)
    lines = detect_lines(edges)
    print(f"lines:({lines})")

    if lines is not None:
        draw_lines(frame, lines)
        
    cv2.imshow("frame", frame)
    cv2.imshow("edges", edges)
    
    cv2.imshow("cropped", cropped_image)

    # Press ESC to exit
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()