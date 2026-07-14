import cv2
import numpy as np
from cv2 import ximgproc

try:
    from .homography import HomographyBEV
except ImportError:  # pragma: no cover - allows direct script execution
    from homography import HomographyBEV


class RoadFeatureDetector:

    def __init__(self, K, camera_height, pitch_deg,yaw_deg,roll_deg, image_size, dist_coeffs=None,
                 min_radius=10, max_radius=200):

        self.bev = HomographyBEV(
            K=np.array(K, dtype=np.float64),
            camera_height=float(camera_height),
            pitch_deg=float(pitch_deg),
            yaw_deg=float(yaw_deg),
            roll_deg=float(roll_deg),
            image_size=tuple(image_size),
            dist_coeffs=None if dist_coeffs is None else np.array(dist_coeffs, dtype=np.float64)
        )

        self.min_radius = min_radius
        self.max_radius = max_radius

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
        cv2.fillPoly(mask, polygon, (255, 255, 255))

        return cv2.bitwise_and(frame, mask)

    # ======================================================
    # EDGE DETECTION
    # ======================================================
    def detect_edges(self, frame):

        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)

        thin = ximgproc.thinning(mask)

        return thin, mask

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
    # CIRCLE DETECTION
    # ======================================================
    def detect_circles(self, image, white_mask):

        blurred = cv2.GaussianBlur(white_mask, (9, 9), 2)
        circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
        param1=50, param2=30,
        minRadius=self.min_radius, maxRadius=self.max_radius
    )

        detected = []
        if circles is not None:
            for x, y, r in np.round(circles[0]).astype(int):
                y0, y1 = max(0, y - r), min(image.shape[0], y + r)
                x0, x1 = max(0, x - r), min(image.shape[1], x + r)
                roi = white_mask[y0:y1, x0:x1]
                if roi.size == 0:
                    continue
                white_ratio = np.sum(roi > 0) / roi.size
                if white_ratio > 0.35:
                    detected.append((int(x), int(y), int(r)))

        # Contour fallback
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < np.pi * (self.min_radius ** 2) or area > np.pi * (self.max_radius ** 2):
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity < 0.6:
                continue
            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            if self.min_radius <= radius <= self.max_radius:
                detected.append((int(cx), int(cy), int(radius)))

        # Merge close duplicates
        merged = []
        for x, y, r in detected:
            dup = False
            for mx, my, mr in merged:
                if np.hypot(mx - x, my - y) < 20:
                    dup = True
                    break
            if not dup:
                merged.append((x, y, r))

        return merged

    # ======================================================
    # MAP CIRCLE CENTER TO GROUND
    # ======================================================
    def circle_to_ground(self, circle):

        x, y, r = circle
        X, Y = self.bev.pixel_to_ground(x, y)
        Xp, Yp = self.bev.pixel_to_ground(x + r, y)
        radius_m = np.hypot(Xp - X, Yp - Y)

        return (X, Y, radius_m)

    # ======================================================
    # CIRCLE POINT CLOUD
    # ======================================================
    def circle_to_ground_cloud(self, circle, num_points=36, filled=False):

        x, y, r = circle
        X, Y = self.bev.pixel_to_ground(x, y)
        Xp, Yp = self.bev.pixel_to_ground(x + r, y)
        radius_m = np.hypot(Xp - X, Yp - Y)

        angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)

        if filled:
            radii = np.linspace(0, radius_m, num=10)
            points = [
                (X + rr * np.cos(a), Y + rr * np.sin(a), 0.0)
                for rr in radii for a in angles
            ]
        else:
            points = [
                (X + radius_m * np.cos(a), Y + radius_m * np.sin(a), 0.0)
                for a in angles
            ]

        return np.array(points, dtype=np.float64)  # (N, 3)

    # ======================================================
    # FIT A SINGLE LINE THROUGH A GROUP OF SEGMENTS
    # ======================================================
    def _fit_line(self, lines_group):
        """Fit x = m*y + b through all endpoints of a group of line segments."""
        if not lines_group:
            return None

        xs, ys = [], []
        for x1, y1, x2, y2 in lines_group:
            xs.extend([x1, x2])
            ys.extend([y1, y2])

        xs = np.array(xs, dtype=np.float64)
        ys = np.array(ys, dtype=np.float64)

        m, b = np.polyfit(ys, xs, 1)  # x as a function of y (stable for near-vertical lines)
        return m, b


    # ======================================================
    # SPLIT LINES INTO LEFT / RIGHT AND FIT EACH
    # ======================================================
    def _fit_left_right_lanes(self, lines):
        left_lines = []
        right_lines = []

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) < 0.3:
                    continue
                if slope < 0:
                    left_lines.append((x1, y1, x2, y2))
                else:
                    right_lines.append((x1, y1, x2, y2))

        left_fit = self._fit_line(left_lines)
        right_fit = self._fit_line(right_lines)

        return left_fit, right_fit


    # ======================================================
    # CONVERT A FITTED LANE LINE TO GROUND-FRAME POINTS
    # ======================================================
    def lane_to_ground_line(self, fit, height, y_top_ratio=0.5):
        """Convert a fitted lane line (x = m*y + b) into two ground points in meters."""
        if fit is None:
            return None

        m, b = fit
        y_bottom = height - 1
        y_top = height * y_top_ratio

        x_bottom = m * y_bottom + b
        x_top = m * y_top + b

        X1, Y1 = self.bev.pixel_to_ground(x_bottom, y_bottom)
        X2, Y2 = self.bev.pixel_to_ground(x_top, y_top)

        return (X1, Y1), (X2, Y2)


    # ======================================================
    # FULL PIPELINE: FRAME -> LEFT/RIGHT LANE LINES IN METERS
    # ======================================================
    def get_lane_lines_ground(self, frame):
        edges, white_mask = self.detect_edges(frame)
        lines = self.detect_lines(edges)
        height = frame.shape[0]

        left_fit, right_fit = self._fit_left_right_lanes(lines)

        return {
            "left":  self.lane_to_ground_line(left_fit, height),
            "right": self.lane_to_ground_line(right_fit, height),
        }
    
    def offsetx_lane(self, frame):
        edges, white_mask = self.detect_edges(frame)
        lines = self.detect_lines(edges)

        frame_center = frame.shape[1] / 2
        height = frame.shape[0]

        if lines is None:
            return 0.0, frame  # no lines detected

        left_x, right_x = self._right_left_lane_x(lines, height)

        if left_x is not None and right_x is not None:
            lane_center = (left_x + right_x) / 2
        elif left_x is not None:
            lane_center = left_x + (frame.shape[1] * 0.25)
        elif right_x is not None:
            lane_center = right_x - (frame.shape[1] * 0.25)
        else:
            return 0.0, frame  # no lanes detected

        y_eval = height - 1  # row near the bottom of the image (close to the vehicle)

        X_lane, _   = self.bev.pixel_to_ground(lane_center, y_eval)
        X_center, _ = self.bev.pixel_to_ground(frame_center, y_eval)

        offset_meters = X_lane - X_center

        cv2.circle(frame, (int(lane_center), height - 50), 10, (255, 0, 0), -1)

        return offset_meters, frame
    
    def _right_left_lane_x(self, lines, y_eval):
        left_lines = []
        right_lines = []
    
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 == x1:
                    continue
                slope = (y2 - y1) / (x2 - x1)
                if abs(slope) < 0.3:
                    continue
                if slope < 0:
                    left_lines.append((x1, y1, x2, y2))
                else:
                    right_lines.append((x1, y1, x2, y2))
    
        def average_x_at_y(lines_group, y_target):
            if not lines_group:
                return None
            xs = []
            for x1, y1, x2, y2 in lines_group:
                slope = (y2 - y1) / (x2 - x1)
                intercept = y1 - slope * x1
                xs.append((y_target - intercept) / slope)
            return np.mean(xs)

        left_x = average_x_at_y(left_lines, y_eval)
        right_x = average_x_at_y(right_lines, y_eval)
        return left_x, right_x

    # ======================================================
    # OFFSET TO WIDEST GAP BETWEEN CIRCLES (HOLES/OBSTACLES)
    # ======================================================
    def offsetx_circle(self, frame):
        """
        Detect circles (holes/obstacles) inside the current lane, find the
        widest gap between them (or between a lane edge and the nearest
        circle), and return the lateral offset in meters from the frame
        center to the center of that gap.
        """
        edges, white_mask = self.detect_edges(frame)
        lines = self.detect_lines(edges)
        circles = self.detect_circles(frame, white_mask)

        height, width = frame.shape[:2]
        y_eval = height - 1
        frame_center_px = width / 2.0

        X_frame_center, _ = self.bev.pixel_to_ground(frame_center_px, y_eval)

        # figure out lane edges (in pixels) at the same row used for offsetx_lane
        x_left_px, x_right_px = self._right_left_lane_x(lines, y_eval)
        if x_left_px is None:
            x_left_px = 0
        if x_right_px is None:
            x_right_px = width

        X_left, _  = self.bev.pixel_to_ground(x_left_px, y_eval)
        X_right, _ = self.bev.pixel_to_ground(x_right_px, y_eval)

        # keep only circles whose center falls within the lane
        lane_circles = [c for c in circles if x_left_px <= c[0] <= x_right_px]

        if not lane_circles:
            return 0.0, frame  # no circles in the lane -> no correction needed

        lane_circles.sort(key=lambda c: c[0])  # sort by pixel x (left to right)

        # convert each circle's left/right edge to ground meters
        ground_edges = []
        for (cx, cy, r) in lane_circles:
            Xg1, _ = self.bev.pixel_to_ground(cx - r, cy)
            Xg2, _ = self.bev.pixel_to_ground(cx + r, cy)
            ground_edges.append((min(Xg1, Xg2), max(Xg1, Xg2)))

        # build gaps: lane_left -> circle1 -> circle2 -> ... -> lane_right
        gaps = [{"start": X_left, "end": ground_edges[0][0]}]
        for i in range(len(ground_edges) - 1):
            gaps.append({"start": ground_edges[i][1], "end": ground_edges[i + 1][0]})
        gaps.append({"start": ground_edges[-1][1], "end": X_right})

        for gap in gaps:
            gap["width"] = gap["end"] - gap["start"]

        best_gap = max(gaps, key=lambda g: g["width"])
        target_center_m = (best_gap["start"] + best_gap["end"]) / 2.0

        offset_meters = target_center_m - X_frame_center

        # visualize detected circles + chosen target
        for (cx, cy, r) in lane_circles:
            cv2.circle(frame, (cx, cy), r, (0, 0, 255), 2)

        return offset_meters, frame

    # ======================================================
    # COMBINED OFFSET: LANE + CIRCLES/OBSTACLES TOGETHER
    # ======================================================
    def get_total_offset(self, frame):
        """
        Runs both the lane offset and the circle/obstacle offset on the same
        frame and returns them individually plus their sum (all in meters),
        along with the annotated frame.
        """
        lane_offset_m, frame = self.offsetx_lane(frame)
        circle_offset_m, frame = self.offsetx_circle(frame)

        total_offset_m = lane_offset_m + circle_offset_m

        return lane_offset_m, circle_offset_m, total_offset_m, frame

    # ======================================================
    # FULL PIPELINE
    # ======================================================
    def process(self, frame, draw_bev=False):

        # --- Lanes ---
        #roi = self.region_of_interest(frame)
        edges, white_mask = self.detect_edges(frame)
        lines = self.detect_lines(edges)
        output = self.draw_lines(frame.copy(), lines)

        # --- Circles ---
        circles = self.detect_circles(frame, white_mask)
        ground_circles = [self.circle_to_ground(c) for c in circles]
        circle_clouds  = [self.circle_to_ground_cloud(c) for c in circles]

        for x, y, r in circles:
            cv2.circle(output, (x, y), r, (0, 255, 0), 2)

        bev_image = None
        if draw_bev:
            bev_image = self.bev.warp_to_bev(output)

        return output, edges, lines, ground_circles, circle_clouds, bev_image


# ======================================================
# MAIN LOOP
# ======================================================
if __name__ == "__main__":

    K = np.array([
        [1000, 0, 960],
        [0, 1000, 540],
        [0, 0, 1]
    ], dtype=np.float64)

    camera_height = 1.2
    pitch_deg = -30

    
    cap = cv2.VideoCapture("D:\\Software_work\\rover_26\\UGVC-Rover-26\\rover_ws\\src\\errors_lane\\errors_lane\\vision\\test.mp4")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("Cannot open video file")
        exit()

    ret, frame = cap.read()
    if not ret:
        print("Cannot read frame from camera")
        exit()

    img_h, img_w = frame.shape[:2]
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    detector = RoadFeatureDetector(
        K=K,
        camera_height=camera_height,
        pitch_deg=pitch_deg,
        image_size=(img_w, img_h),
        yaw_deg=0,
        roll_deg=0
    )
    
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        output, edges, lines, ground_circles, circle_clouds, bev = detector.process(frame, draw_bev=True)
        print("Ground circles:", ground_circles)
        #print("lines:", lines)

        lane_offset_m, circle_offset_m, total_offset_m, output = detector.get_total_offset(output)
        print(f"Lane offset: {lane_offset_m:.3f} m | Circle offset: {circle_offset_m:.3f} m | Total: {total_offset_m:.3f} m")

        for i, cloud in enumerate(circle_clouds):
            print(f"  circle {i+1} cloud points: {len(cloud)}")

        #roi = detector.region_of_interest(frame)
        cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Video", 640, 480)
        #cv2.imshow("ROI", roi)
        cv2.imshow("Video", output)
        cv2.imshow("Edges", edges)
        if bev is not None:
            cv2.imshow("BEV", bev)
            

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()