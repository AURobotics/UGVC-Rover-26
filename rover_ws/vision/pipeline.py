import cv2
import numpy as np

from homography import HomographyBEV
from road_features_detector import RoadFeatureDetector


# =============================================================
# HELPERS
# =============================================================

def lines_to_mask(lines, shape):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    if lines is None:
        return mask
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=2)
    return mask


def mask_to_pixels(mask):
    ys, xs = np.where(mask > 0)
    return np.stack([xs, ys], axis=1).astype(np.float64)


# =============================================================
# PIPELINE CLASS
# =============================================================

class RoadFeatureBEVPipeline:

    def __init__(self, K, camera_height, pitch_deg, image_size):

        self.detector = RoadFeatureDetector(
            K=K,
            camera_height=camera_height,
            pitch_deg=pitch_deg,
            image_size=image_size,
        )

        self.bev = self.detector.bev  # reuse same HomographyBEV instance

    # ----------------------------------------------------------
    # PROCESS A SINGLE FRAME
    # ----------------------------------------------------------

    def process_frame(self, frame):
        """
        Returns
        -------
        output          : annotated BGR frame (lanes + circles drawn)
        bev_image       : bird's-eye-view warp of the frame
        lane_mask       : rasterised detected-line mask
        lane_points     : (N, 3) float64 lane ground point cloud [X, Y, 0]
        ground_circles  : list of (X, Y, radius_m) center tuples
        circle_clouds   : list of (N, 3) arrays, one per detected circle
        """

        # 1. Run detector (lanes + circles) ─────────────────────
        output, edges, lines, ground_circles, circle_clouds, _ = \
            self.detector.process(frame, draw_bev=False)

        # 2. Rasterise detected lines → mask ─────────────────────
        lane_mask = lines_to_mask(lines, frame.shape)

        # 3. Project lane mask pixels → ground plane ─────────────
        pixels = mask_to_pixels(lane_mask)

        if len(pixels) == 0:
            lane_points = np.zeros((0, 3), dtype=np.float64)
        else:
            xy          = self.bev.pixels_to_ground(pixels)
            z           = np.zeros((len(xy), 1), dtype=np.float64)
            lane_points = np.hstack([xy, z])

        # 4. BEV warp ────────────────────────────────────────────
        bev_image = self.bev.warp_to_bev(frame)

        return output, bev_image, lane_mask, lane_points, ground_circles, circle_clouds

    # ----------------------------------------------------------
    # SAVE HELPERS
    # ----------------------------------------------------------

    def save_pcd(self, points, filename="lane_cloud.pcd"):
        self.bev.save_pcd(points, filename)


# =============================================================
# MAIN LOOP
# =============================================================

def main():

    K = np.array([
        [1000,    0, 960],
        [   0, 1000, 540],
        [   0,    0,   1],
    ], dtype=np.float64)

    cap = cv2.VideoCapture("../data/raw/test_lane.mp4")

    if not cap.isOpened():
        print("Cannot open video file")
        return

    ret, first_frame = cap.read()
    if not ret:
        print("Cannot read video")
        return

    h, w = first_frame.shape[:2]
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    pipeline = RoadFeatureBEVPipeline(
        K=K,
        camera_height=1.43,
        pitch_deg=-50,
        image_size=(w, h),
    )

    frame_idx  = 0
    all_points = []

    while True:

        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        output, bev_image, lane_mask, lane_points, ground_circles, circle_clouds = \
            pipeline.process_frame(frame)

        print(f"[frame {frame_idx:04d}] "
              f"lane pixels: {len(lane_points):6d}  "
              f"circles: {len(ground_circles)}")

        for i, (cloud, (X, Y, rm)) in enumerate(zip(circle_clouds, ground_circles)):
            print(f"  circle {i+1}: center=({X:.2f}m, {Y:.2f}m)  "
                  f"r={rm:.2f}m  cloud_pts={len(cloud)}")

        #if frame_idx % 30 == 0 and len(lane_points) > 0:
        #    pipeline.save_pcd(lane_points, f"lane_cloud_{frame_idx:04d}.pcd")

        all_points.append(lane_points)

        cv2.imshow("Road Features", output)
        cv2.imshow("Lane Mask",     lane_mask)
        cv2.imshow("BEV",           bev_image)

        key = cv2.waitKey(1)
        if key == 27:
            break
        if key == ord('s') and len(lane_points) > 0:
            pipeline.save_pcd(lane_points, f"lane_cloud_manual_{frame_idx:04d}.pcd")
            print(f"  → saved lane_cloud_manual_{frame_idx:04d}.pcd")

        frame_idx += 1

    if all_points:
        merged = np.vstack([p for p in all_points if len(p) > 0])
        pipeline.save_pcd(merged, "lane_cloud_full.pcd")
        print(f"Saved merged cloud: {len(merged)} points")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()