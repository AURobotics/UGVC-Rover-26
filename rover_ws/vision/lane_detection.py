import cv2
import numpy as np
from cv2 import ximgproc

class LaneDetector:

    def __init__(self):
        self.lower_white = np.array([0, 0, 200])
        self.upper_white = np.array([180, 50, 255])
        self.kernel = np.ones((5, 5), np.uint8)

    # ======================================================
    # ROI (kept separate, NOT used in pipeline by default)
    # ======================================================
    def region_of_interest(self, frame):

        height, width = frame.shape[:2]

        polygon = np.array([[
            (0, height),
            (width, height),
            (width // 2 + 150, height // 2),
            (width // 2 - 150, height // 2)
        ]], np.int32)

        mask = np.zeros_like(frame)
        cv2.fillPoly(mask, polygon, 255)

        return cv2.bitwise_and(frame, mask)

    # ======================================================
    # EDGE DETECTION (MATCHES YOUR ORIGINAL PIPELINE)
    # ======================================================
    def detect_edges(self, frame):

        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)

        thin = ximgproc.thinning(mask)

        return thin

    # ======================================================
    # HOUGH LINES
    # ======================================================
    def detect_lines(self, edges):

        lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            50,
            minLineLength=50,
            maxLineGap=30
        )

        return lines

    # ======================================================
    # DRAW LINES
    # ======================================================
    def draw_lines(self, frame, lines):

        if lines is None:
            return frame

        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 5)

        return frame

    # ======================================================
    # FULL PIPELINE (NO ROI BY DEFAULT → matches your working code)
    # ======================================================
    def process(self, frame):

        edges = self.detect_edges(frame)
        lines = self.detect_lines(edges)

        output = self.draw_lines(frame.copy(), lines)

        return output, edges, lines


# ======================================================
# MAIN LOOP 
# ======================================================
if __name__ == "__main__":
    cap = cv2.VideoCapture("../data/raw/test_lane.mp4")

    if not cap.isOpened():
        print("Cannot open video file")
        exit()

    detector = LaneDetector()

    while True:

        ret, frame = cap.read()

        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        output, edges, lines = detector.process(frame)

        print("lines:", lines)

        cv2.imshow("frame", output)
        cv2.imshow("edges", edges)

        key = cv2.waitKey(1)
        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()