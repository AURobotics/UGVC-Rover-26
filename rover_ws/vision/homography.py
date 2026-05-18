import cv2
import numpy as np


class HomographyBEV:

    def __init__(
        self,
        K,
        camera_height,
        pitch_deg,
        image_size,
        dist_coeffs=None
    ):

        self.K = K.astype(np.float64)

        self.dist_coeffs = (
            np.zeros(5, dtype=np.float64)
            if dist_coeffs is None
            else dist_coeffs.astype(np.float64)
        )

        self.camera_height = camera_height
        self.pitch_deg = pitch_deg
        self.pitch = np.deg2rad(pitch_deg)

        self.img_w = image_size[0]
        self.img_h = image_size[1]

        self._build_extrinsics()
        self._build_homography()
        self._build_bev_scaling()

    # =========================================================
    # BUILD EXTRINSICS
    # =========================================================

    def _build_extrinsics(self):

        cp = np.cos(self.pitch)
        sp = np.sin(self.pitch)

        # World-to-camera rotation
        self.R = np.array([
            [-1, 0, 0],
            [0, cp, -sp],
            [0, sp,  cp]
        ], dtype=np.float64)

        # Camera position in world frame
        C = np.array([
            [0],
            [0],
            [self.camera_height]
        ], dtype=np.float64)

        # Proper translation
        self.t = -self.R @ C

    # =========================================================
    # BUILD HOMOGRAPHY
    # =========================================================

    def _build_homography(self):

        H = np.column_stack((self.R[:, 0], self.R[:, 1], self.t))

        self.H = self.K @ H
        self.H_inv = np.linalg.inv(self.H)

    # =========================================================
    # BUILD BEV SCALE
    # =========================================================

    def _build_bev_scaling(self):

        corners_px = np.array([
            [0, self.img_h *0.5],
            [self.img_w - 1, self.img_h *0.5],
            [0, self.img_h - 1],
            [self.img_w - 1, self.img_h - 1],
        ], dtype=np.float64)

        world_pts = []

        for (u, v) in corners_px:

            ground = self.H_inv @ np.array([u, v, 1.0])
            ground /= ground[2]

            world_pts.append((ground[0], ground[1]))

        world_pts = np.array(world_pts)

        x_min = world_pts[:, 0].min()
        x_max = world_pts[:, 0].max()

        y_min = world_pts[:, 1].min()
        y_max = world_pts[:, 1].max()

        self.out_w = self.img_w
        self.out_h = self.img_h // 2

        scale = min(
            self.out_w / (x_max - x_min),
            self.out_h / (y_max - y_min)
        )

        self.S = np.array([
            [scale, 0, -scale * x_min],
            [0, -scale, scale * y_max],
            [0, 0, 1]
        ], dtype=np.float64)

        self.S_inv = np.linalg.inv(self.S)

        self.H_bev = self.S @ self.H_inv

    # =========================================================
    # PIXEL -> GROUND
    # =========================================================

    def pixel_to_ground(self, u, v):

        pixel = np.array([u, v, 1.0], dtype=np.float64)

        ground = self.H_inv @ pixel
        ground /= ground[2]

        return ground[0], ground[1]

    # =========================================================
    # MULTIPLE PIXELS -> GROUND
    # =========================================================

    def pixels_to_ground(self, pixels):

        pixels = np.asarray(pixels, dtype=np.float64)

        px = np.stack([
            pixels[:, 0],
            pixels[:, 1],
            np.ones(len(pixels))
        ], axis=0)

        ground = self.H_inv @ px
        ground /= ground[2]

        X = ground[0]
        Y = ground[1]

        return np.stack([X, Y], axis=1)

    # =========================================================
    # MASK -> POINT CLOUD
    # =========================================================

    def mask_to_pointcloud(self, mask):

        ys, xs = np.where(mask > 0)

        px = np.stack([
            xs.astype(np.float64),
            ys.astype(np.float64),
            np.ones_like(xs, dtype=np.float64)
        ], axis=0)

        ground = self.H_inv @ px
        ground /= ground[2]

        X = ground[0]
        Y = ground[1]
        Z = np.zeros_like(X)

        points = np.stack([X, Y, Z], axis=1)

        return points

    # =========================================================
    # WARP IMAGE TO BEV
    # =========================================================

    def warp_to_bev(self, image):

        bev = cv2.warpPerspective(
            image,
            self.H_bev,
            (self.out_w, self.out_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )

        #bev = cv2.flip(bev, 0)

        return bev

    # =========================================================
    # SAVE PCD
    # =========================================================

    def save_pcd(self, points, filename):

        n = len(points)

        header = (
            f"# .PCD v0.7\n"
            f"FIELDS x y z\n"
            f"SIZE 4 4 4\n"
            f"TYPE F F F\n"
            f"COUNT 1 1 1\n"
            f"WIDTH {n}\n"
            f"HEIGHT 1\n"
            f"VIEWPOINT 0 0 0 1 0 0 0\n"
            f"POINTS {n}\n"
            f"DATA ascii\n"
        )

        with open(filename, 'w') as f:

            f.write(header)
            np.savetxt(f, points, fmt="%.4f")

        print(f"Saved: {filename}")


# =============================================================
# EXAMPLE USAGE
# =============================================================
if __name__ == "__main__":
    image = cv2.imread("../data/raw/ground.jpeg")

    h, w = image.shape[:2]

    K = np.array([
        [1000, 0, w/2],
        [0, 1000, h/2],
        [0, 0, 1]
    ], dtype=np.float64)

    bev = HomographyBEV(
        K=K,
        camera_height=1.43,
        pitch_deg=-45,
        image_size=(w, h)
    )
    print(f"w={w}\nh={h}")
    # =============================================================
    # SINGLE PIXEL
    # =============================================================
    X, Y = bev.pixel_to_ground(442,620)

    print(f"Ground point: X={X:.3f}, Y={Y:.3f}")

    # =============================================================
    # WARP FULL IMAGE
    # =============================================================

    bird_eye = bev.warp_to_bev(image)

    # =============================================================
    # MASK -> POINT CLOUD
    # =============================================================

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, mask = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

    points = bev.mask_to_pointcloud(mask)

    print("Point cloud shape:", points.shape)

    bev.save_pcd(points, "ground_plane.pcd")

    # =============================================================
    # DISPLAY
    # =============================================================

    cv2.imshow("Original", image)
    cv2.imshow("Mask", mask)
    cv2.imshow("Bird Eye", bird_eye)

    cv2.waitKey(0)
    cv2.destroyAllWindows()