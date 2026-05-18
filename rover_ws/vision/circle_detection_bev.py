import cv2
import numpy as np
from homography import HomographyBEV


class CircleDetectorBEV:

    def __init__(self, K, camera_height, pitch_deg, image_size, dist_coeffs=None,
                 min_radius=10, max_radius=200):
        self.bev = HomographyBEV(
            K=np.array(K, dtype=np.float64),
            camera_height=float(camera_height),
            pitch_deg=float(pitch_deg),
            image_size=tuple(image_size),
            dist_coeffs=None if dist_coeffs is None else np.array(dist_coeffs, dtype=np.float64)
        )

        self.min_radius = min_radius
        self.max_radius = max_radius

    # -----------------------
    # Circle detection
    # -----------------------
    def _detect_circles(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 40, 255])

        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)

        # Hough on blurred mask
        blurred = cv2.GaussianBlur(white_mask, (9, 9), 2)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
            param1=50, param2=30,
            minRadius=self.min_radius, maxRadius=self.max_radius
        )

        detected = []
        if circles is not None:
            for x, y, r in np.round(circles[0]).astype(int):
                # validate white ratio inside circle
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

        # merge close duplicates
        merged = []
        for x, y, r in detected:
            dup = False
            for i, (mx, my, mr) in enumerate(merged):
                if np.hypot(mx - x, my - y) < 20:
                    dup = True
                    break
            if not dup:
                merged.append((x, y, r))

        return merged

    # -----------------------
    # Map circles to ground coordinates
    # -----------------------
    def circle_to_ground(self, circle):
        x, y, r = circle
        X, Y = self.bev.pixel_to_ground(x, y)
        # approximate radius in meters by mapping center and center+radius in image
        xp, yp = x + r, y
        Xp, Yp = self.bev.pixel_to_ground(xp, yp)
        radius_m = np.hypot(Xp - X, Yp - Y)
        return (X, Y, radius_m)

    # -----------------------
    # Full process
    # -----------------------
    def process(self, image, draw_bev=False):
        circles = self._detect_circles(image)

        ground_circles = [self.circle_to_ground(c) for c in circles]

        annotated = image.copy()
        for i, (x, y, r) in enumerate(circles):
            cv2.circle(annotated, (x, y), r, (0, 255, 0), 2)
            cv2.circle(annotated, (x, y), 3, (0, 0, 255), -1)
            X, Y, rm = ground_circles[i]
            cv2.putText(annotated, f"{i+1}: ({X:.2f}m,{Y:.2f}m) r={rm:.2f}m",
                        (x - 30, y - r - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        bev_image = None
        if draw_bev:
            bev_image = self.bev.warp_to_bev(annotated)

        return annotated, bev_image, ground_circles


# -----------------------
# Main Loop
# -----------------------
if __name__ == "__main__":
    # Basic K example; replace with your calibrated intrinsics
    K = np.array([
        [1000, 0, 960],
        [0, 1000, 540],
        [0, 0, 1]
    ], dtype=np.float64)

    # Adjust these to match your camera
    camera_height = 1.2
    pitch_deg = -30

    cap = cv2.VideoCapture("D:\\Software work\\rover 26\\test_lane.mp4")
    if not cap.isOpened():
        print("Cannot open camera, try changing source")
        exit()

    ret, frame = cap.read()
    if not ret:
        print("Cannot read frame from camera")
        exit()

    img_h, img_w = frame.shape[:2]

    detector = CircleDetectorBEV(K=K, camera_height=camera_height, pitch_deg=pitch_deg,
                                 image_size=(img_w, img_h))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        annotated, bev, circles = detector.process(frame, draw_bev=True)
        print("Detected circles (X, Y, radius_m):", circles)
        cv2.imshow("Annotated", annotated)
        if bev is not None:
            cv2.imshow("BEV", bev)

        key = cv2.waitKey(1)
        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
