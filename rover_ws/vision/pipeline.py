import cv2
import numpy as np

from homography import HomographyBEV
from lane_detection import LaneDetector


# =============================================================
# HELPERS
# =============================================================

def lines_to_mask(lines, shape):
    """
    Rasterise HoughLinesP segments onto a blank mask so we get
    only the *detected-line* pixels, not the full edge image.
    """
    mask = np.zeros(shape[:2], dtype=np.uint8)

    if lines is None:
        return mask

    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=2)

    return mask


def mask_to_pixels(mask):
    """
    Return (N, 2) array of [u, v] pixel coordinates where mask > 0.
    """
    ys, xs = np.where(mask > 0)
    return np.stack([xs, ys], axis=1).astype(np.float64)


# =============================================================
# PIPELINE CLASS
# =============================================================

class LaneBEVPipeline:

    def __init__(self, K, camera_height, pitch_deg, image_size):

        self.detector = LaneDetector()

        self.bev = HomographyBEV(
            K=K,
            camera_height=camera_height,
            pitch_deg=pitch_deg,
            image_size=image_size,
        )

    # ----------------------------------------------------------
    # PROCESS A SINGLE FRAME
    # ----------------------------------------------------------

    def process_frame(self, frame):
        """
        Run the full pipeline on one BGR frame.

        Returns
        -------
        output      : annotated BGR frame from lane detector
        bev_image   : bird's-eye-view warp of the *frame*
        lane_mask   : rasterised detected-line mask
        points      : (N, 3) float32 ground-plane point cloud  [X, Y, 0]
        """

        # 1. Lane detection ─────────────────────────────────────
        output, edges, lines = self.detector.process(frame)

        # 2. Rasterise only the *detected lines* onto a mask ────
        lane_mask = lines_to_mask(lines, frame.shape)

        # 3. Project mask pixels → ground plane ─────────────────
        pixels = mask_to_pixels(lane_mask)

        if len(pixels) == 0:
            points = np.zeros((0, 3), dtype=np.float64)
        else:
            xy = self.bev.pixels_to_ground(pixels)     # (N, 2)
            z  = np.zeros((len(xy), 1), dtype=np.float64)
            points = np.hstack([xy, z])                # (N, 3)  [X, Y, 0]

        # 4. BEV warp (visual debug) ─────────────────────────────
        bev_image = self.bev.warp_to_bev(frame)

        return output, bev_image, lane_mask, points

    # ----------------------------------------------------------
    # SAVE HELPERS
    # ----------------------------------------------------------

    def save_pcd(self, points, filename="lane_cloud.pcd"):
        self.bev.save_pcd(points, filename)


# =============================================================
# MAIN LOOP
# =============================================================

def main():

    # ── Camera intrinsics (adjust to your camera) ───────────────
    K = np.array([
        [1000,    0, 960],
        [   0, 1000, 540],
        [   0,    0,   1],
    ], dtype=np.float64)

    cap = cv2.VideoCapture("../data/raw/test_lane.mp4")

    if not cap.isOpened():
        print("Cannot open video file")
        return

    # Read the first frame to get resolution
    ret, first_frame = cap.read()
    if not ret:
        print("Cannot read video")
        return

    h, w = first_frame.shape[:2]

    # Reset to start
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # ── Build pipeline ───────────────────────────────────────────
    pipeline = LaneBEVPipeline(
        K=K,
        camera_height=1.43,   # metres
        pitch_deg=-50,
        image_size=(w, h),
    )

    frame_idx   = 0
    all_points  = []           # accumulate across frames if desired

    while True:

        ret, frame = cap.read()

        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        output, bev_image, lane_mask, points = pipeline.process_frame(frame)

        print(f"[frame {frame_idx:04d}] "
              f"lane pixels: {len(points):6d}  "
              f"| sample XY: {points[:2, :2] if len(points) >= 2 else '—'}")

        # ── Optional: save PCD every N frames ───────────────────
        if frame_idx % 30 == 0 and len(points) > 0:
            pipeline.save_pcd(points, f"lane_cloud_{frame_idx:04d}.pcd")

        # ── Accumulate (comment out if memory is a concern) ─────
        all_points.append(points)

        # ── Visualise ───────────────────────────────────────────
        # Overlay lane mask in red on the BEV for a quick debug view
        bev_debug = cv2.cvtColor(bev_image, cv2.COLOR_BGR2RGB) \
            if len(bev_image.shape) == 3 else bev_image.copy()

        cv2.imshow("Lane Detection",  output)
        cv2.imshow("Lane Mask",       lane_mask)
        cv2.imshow("BEV",             bev_image)

        key = cv2.waitKey(1)
        if key == 27:          # ESC → quit
            break
        if key == ord('s') and len(points) > 0:   # S → save current frame
            pipeline.save_pcd(points, f"lane_cloud_manual_{frame_idx:04d}.pcd")
            print(f"  → saved lane_cloud_manual_{frame_idx:04d}.pcd")

        frame_idx += 1

    # ── (Optional) save the full accumulated cloud ───────────────
    if all_points:
        merged = np.vstack([p for p in all_points if len(p) > 0])
        pipeline.save_pcd(merged, "lane_cloud_full.pcd")
        print(f"Saved merged cloud: {len(merged)} points")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()