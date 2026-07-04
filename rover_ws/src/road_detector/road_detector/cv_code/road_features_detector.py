import cv2
import numpy as np
from cv2 import ximgproc
from .homography import HomographyBEV


class RoadFeatureDetector:

    def __init__(self, K, camera_height, pitch_deg,yaw_deg,roll_deg, image_size, dist_coeffs=None,
                 min_radius=10, max_radius=200, horizon_margin_px=20, max_forward_range=5.0):

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

        # How many extra pixels below the mathematical horizon row to
        # additionally exclude, since points very close to the horizon
        # are numerically unstable (tiny pitch/pixel errors -> huge
        # distance swings) even though they're technically "below" it.
        self.horizon_margin_px = horizon_margin_px

        # Ground points farther than this (in meters) are treated as
        # unreliable noise and dropped, rather than trusted at face value.
        self.max_forward_range = max_forward_range

        self.lower_white = np.array([0, 0, 200])
        self.upper_white = np.array([180, 50, 255])
        self.kernel = np.ones((5, 5), np.uint8)

        self._update_horizon_roi()

    # ======================================================
    # HORIZON ROI
    # ======================================================
    def _update_horizon_roi(self):
        """
        Recompute the topmost image row that is safe to run ground-plane
        detection on, based on the current homography. Call this again
        any time the underlying HomographyBEV's camera_height/pitch_deg/
        yaw_deg/roll_deg change and its extrinsics are rebuilt.
        """
        row = self.bev.horizon_row()

        if row is None or row < 0:
            # No usable horizon in frame (e.g. camera pitched so far down
            # the whole image is below it) -- don't crop anything.
            self.roi_top_row = 0
        else:
            self.roi_top_row = int(np.clip(
                row + self.horizon_margin_px, 0, self.bev.img_h
            ))

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
    # EDGE DETECTION
    # ======================================================
    def detect_edges(self, frame):

        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)

        # Blank out everything at/above the horizon (+ margin). Those rows
        # don't correspond to real ground points -- keeping them here
        # would let sky/background pixels get treated as lane markings
        # and later blow up into garbage ground-plane coordinates.
        if self.roi_top_row > 0:
            mask[:self.roi_top_row, :] = 0

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
    def _detect_circles(self, image, white_mask):

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
    # RANGE VALIDITY CHECK
    # ======================================================
    def _is_valid_ground_range(self, Y):
        """
        Y <= 0 means the point is at/behind the horizon (not real ground
        in front of the camera). Y beyond max_forward_range is treated as
        unreliable, since points get numerically unstable near the horizon.
        """
        return 0.0 < Y <= self.max_forward_range

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
    # FULL PIPELINE
    # ======================================================
    def process(self, frame, draw_bev=False):

        # --- Lanes ---
        edges, white_mask = self.detect_edges(frame)
        lines = self.detect_lines(edges)
        output = self.draw_lines(frame.copy(), lines)

        # --- Circles ---
        raw_circles = self._detect_circles(frame, white_mask)

        circles = []
        ground_circles = []
        circle_clouds = []
        for c in raw_circles:
            X, Y, radius_m = self.circle_to_ground(c)
            if not self._is_valid_ground_range(Y):
                continue
            circles.append(c)
            ground_circles.append((X, Y, radius_m))
            circle_clouds.append(self.circle_to_ground_cloud(c))

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

    cap = cv2.VideoCapture("../data/raw/test_lane.mp4")
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

        output, edges, lines, ground_circles, circle_clouds, bev = \
            detector.process(frame, draw_bev=True)

        print("Ground circles:", ground_circles)
        for i, cloud in enumerate(circle_clouds):
            print(f"  circle {i+1} cloud points: {len(cloud)}")

        cv2.imshow("Road Features", output)
        cv2.imshow("Edges", edges)
        if bev is not None:
            cv2.imshow("BEV", bev)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()