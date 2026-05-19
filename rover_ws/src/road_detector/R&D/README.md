# Road Feature BEV Pipeline

A computer vision pipeline for detecting road features (lane markings, circular road signs/markings) from a forward-facing camera and projecting them onto a Bird's-Eye View (BEV) ground plane using homography.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Modules](#modules)
  - [homography.py](#homographypy)
  - [road_features_detector.py](#road_features_detectorpy)
  - [pipeline.py](#pipelinepy)
- [Installation](#installation)
- [Camera Calibration Parameters](#camera-calibration-parameters)
- [Usage](#usage)
  - [Running the Full Pipeline](#running-the-full-pipeline)
  - [Running the Detector Standalone](#running-the-detector-standalone)
  - [Using HomographyBEV Directly](#using-homographybev-directly)
- [Output Reference](#output-reference)
- [Configuration Guide](#configuration-guide)
- [Keyboard Controls](#keyboard-controls)
- [Coordinate System](#coordinate-system)

---

## Overview

This system takes a video stream from a vehicle-mounted camera and performs:

1. **White lane marking detection** via HSV color filtering + Hough line transform
2. **Circular road marking detection** via Hough circles + contour circularity analysis
3. **Ground plane projection** of all detections using a planar homography derived from known camera intrinsics, mounting height, and pitch angle
4. **Bird's-Eye View warping** of the full image for spatial visualization
5. **Point cloud export** of lane and circle detections in `.pcd` format (compatible with CloudCompare, Open3D, RViz, etc.)

No stereo camera, LiDAR, or depth sensor is required — the ground plane assumption and known camera geometry are sufficient for metric reconstruction.

---

## Architecture

```
pipeline.py
│
├── RoadFeatureBEVPipeline
│   ├── RoadFeatureDetector  (road_features_detector.py)
│   │   ├── detect_edges()       — HSV masking + morphology + thinning
│   │   ├── detect_lines()       — Probabilistic Hough line transform
│   │   ├── _detect_circles()    — Hough circles + contour fallback
│   │   ├── circle_to_ground()   — Projects circle center to world (X, Y, r_m)
│   │   └── circle_to_ground_cloud() — Generates a ring/disk point cloud
│   │
│   └── HomographyBEV  (homography.py)
│       ├── pixel_to_ground()    — Single pixel → world (X, Y)
│       ├── pixels_to_ground()   — Batch pixels → world
│       ├── mask_to_pointcloud() — Full mask → (N, 3) XYZ point cloud
│       ├── warp_to_bev()        — Warp full image to BEV
│       └── save_pcd()           — Write ASCII .pcd file
```

The `RoadFeatureBEVPipeline` is the recommended entry point. It instantiates the detector (which internally creates and owns a `HomographyBEV` instance), so the same homography is shared across all projection operations.

---

## Modules

### `homography.py`

Implements the `HomographyBEV` class. This is the geometric core of the system.

**How it works:**

Given camera intrinsics `K`, mounting height above the ground, and a downward pitch angle, it constructs:

- A world-to-camera rotation matrix `R` (pure pitch rotation, no roll or yaw)
- A translation vector `t` placing the camera at `[0, 0, camera_height]` in the world frame
- A homography `H = K · [R[:,0] | R[:,1] | t]` mapping ground-plane world points to image pixels
- Its inverse `H_inv` for back-projecting image pixels to the ground plane
- A BEV scaling matrix `S` that maps ground-plane coordinates to a top-down output image

The BEV output size is `(img_w, img_h // 2)` by default, scaled to fit the visible ground region.

**Key constructor parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `K` | `np.ndarray (3×3)` | Camera intrinsic matrix |
| `camera_height` | `float` | Camera height above ground in **meters** |
| `pitch_deg` | `float` | Camera pitch in degrees. **Negative = looking down** |
| `image_size` | `tuple (w, h)` | Input image dimensions in pixels |
| `dist_coeffs` | `np.ndarray`, optional | OpenCV distortion coefficients (not yet applied to warp) |

---

### `road_features_detector.py`

Implements `RoadFeatureDetector`, which wraps `HomographyBEV` and adds all CV detection logic.

**Lane detection pipeline:**

1. Gaussian blur → HSV conversion
2. White color mask: `H ∈ [0,180]`, `S ∈ [0,50]`, `V ∈ [200,255]`
3. Morphological open + close to remove noise
4. Skeletonization via `cv2.ximgproc.thinning`
5. Probabilistic Hough line transform (`HoughLinesP`)

**Circle detection pipeline:**

1. Same white HSV mask as above (tighter saturation: `S ≤ 40`)
2. Gaussian blur → `HoughCircles` with gradient method
3. Per-circle white-pixel ratio check (must be > 35% within bounding box)
4. Contour-based fallback: circularity `= 4π·area / perimeter² > 0.6`
5. Duplicate merging: detections within 20 px of each other are collapsed

**Constructor parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `K` | `np.ndarray (3×3)` | Camera intrinsic matrix |
| `camera_height` | `float` | Meters |
| `pitch_deg` | `float` | Degrees (negative = down) |
| `image_size` | `tuple (w, h)` | Pixels |
| `dist_coeffs` | optional | Distortion coefficients |
| `min_radius` | `int` | Minimum circle radius in pixels (default: `10`) |
| `max_radius` | `int` | Maximum circle radius in pixels (default: `200`) |

---

### `pipeline.py`

Implements `RoadFeatureBEVPipeline`, the top-level orchestrator for video processing.

`process_frame(frame)` returns:

| Return value | Type | Description |
|---|---|---|
| `output` | `np.ndarray` | Annotated BGR frame with lanes and circles drawn |
| `bev_image` | `np.ndarray` | BEV warp of the raw frame |
| `lane_mask` | `np.ndarray` | Binary mask of rasterized Hough lines |
| `lane_points` | `(N, 3) float64` | Lane ground-plane point cloud `[X, Y, 0]` |
| `ground_circles` | `list of (X, Y, r_m)` | Circle centers + radii in meters |
| `circle_clouds` | `list of (N, 3) arrays` | Per-circle ring point clouds in meters |

---

## Installation

**Requirements:** Python 3.8+

```bash
pip install opencv-python opencv-contrib-python numpy
```

> `opencv-contrib-python` is required for `cv2.ximgproc.thinning` (skeletonization) and `cv2.HoughCircles`. Do not install both `opencv-python` and `opencv-contrib-python` simultaneously — they conflict.

**Verify install:**

```python
import cv2
from cv2 import ximgproc
print(cv2.__version__)
```

**Optional — point cloud viewers:**

- [Open3D](http://www.open3d.org/) — `pip install open3d`
- [CloudCompare](https://www.cloudcompare.org/) — GUI application
- RViz (ROS) — for robotics integration

---

## Camera Calibration Parameters

The intrinsic matrix `K` must match your actual camera. The assumed format is:

```
K = [[fx,  0, cx],
     [ 0, fy, cy],
     [ 0,  0,  1]]
```

Where:
- `fx`, `fy` — focal lengths in pixels
- `cx`, `cy` — principal point (typically near the image center)

To obtain `K` for your camera, use OpenCV's checkerboard calibration:

```python
# Approximate K for a 1920×1080 camera with ~90° horizontal FOV:
K = np.array([
    [960,   0, 960],
    [  0, 960, 540],
    [  0,   0,   1]
], dtype=np.float64)
```

**Pitch convention:** Negative pitch means the camera is angled downward (typical for a dashboard or bumper mount). A pitch of `-50°` is a steep downward angle, while `-10°` is nearly horizontal.

---

## Usage

### Running the Full Pipeline

Edit the camera parameters in `pipeline.py` and point to your video file:

```python
K = np.array([
    [1000,    0, 960],
    [   0, 1000, 540],
    [   0,    0,   1],
], dtype=np.float64)

cap = cv2.VideoCapture("path/to/your/video.mp4")

pipeline = RoadFeatureBEVPipeline(
    K=K,
    camera_height=1.43,   # meters above ground
    pitch_deg=-50,         # negative = looking down
    image_size=(w, h),
)
```

Then run:

```bash
python pipeline.py
```

Three windows will appear:
- **Road Features** — annotated frame with green lane lines and circles
- **Lane Mask** — binary mask of detected lines
- **BEV** — bird's-eye view of the frame

When the video ends, it loops. A merged point cloud of all frames is saved automatically as `lane_cloud_full.pcd`.

---

### Running the Detector Standalone

```bash
python road_features_detector.py
```

This opens the same video and shows:
- **Road Features** — annotated frame
- **Edges** — thinned white-pixel skeleton
- **BEV** — warped output with annotations

Ground circle coordinates are printed to the console each frame.

---

### Using HomographyBEV Directly

```python
import cv2
import numpy as np
from homography import HomographyBEV

image = cv2.imread("frame.jpg")
h, w = image.shape[:2]

K = np.array([
    [1000,    0, w / 2],
    [   0, 1000, h / 2],
    [   0,    0,     1],
], dtype=np.float64)

bev = HomographyBEV(
    K=K,
    camera_height=1.43,
    pitch_deg=-45,
    image_size=(w, h)
)

# Project a single pixel to the ground plane
X, Y = bev.pixel_to_ground(u=640, v=500)
print(f"World position: X={X:.3f} m, Y={Y:.3f} m")

# Warp the full image to BEV
bird_eye = bev.warp_to_bev(image)

# Convert a binary mask to a 3D point cloud
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
_, mask = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
points = bev.mask_to_pointcloud(mask)  # (N, 3) array

# Save as .pcd
bev.save_pcd(points, "output.pcd")

cv2.imshow("BEV", bird_eye)
cv2.waitKey(0)
```

---

## Output Reference

### Point Cloud (`.pcd`)

Saved in ASCII PCD v0.7 format with fields `x y z` (meters). Z is always `0.0` since all points are projected to the ground plane.

Compatible with Open3D:

```python
import open3d as o3d
pcd = o3d.io.read_point_cloud("lane_cloud_full.pcd")
o3d.visualization.draw_geometries([pcd])
```

### Ground Circle Tuple

Each entry in `ground_circles` is `(X, Y, radius_m)`:

- `X` — lateral offset from camera in meters (positive = right)
- `Y` — forward distance from camera in meters (positive = forward)
- `radius_m` — estimated radius of the circle in meters

---

## Configuration Guide

| Goal | Parameter to change |
|---|---|
| Adjust how far ahead lanes are detected | Increase `pitch_deg` magnitude or raise `camera_height` |
| Detect smaller circles (e.g. painted dots) | Lower `min_radius` in `RoadFeatureDetector` |
| Detect larger circles (e.g. roundabouts) | Raise `max_radius` |
| Reduce false positive lanes | Increase `threshold` in `HoughLinesP` or `minLineLength` |
| Detect yellow lanes as well | Extend HSV range in `detect_edges` / `_detect_circles` |
| Save point clouds every N frames | Uncomment the `save_pcd` call inside `main()` in `pipeline.py` |
| Improve accuracy on fisheye cameras | Pass `dist_coeffs` from OpenCV calibration to the constructor |

---

## Keyboard Controls

When any pipeline window is in focus:

| Key | Action |
|-----|--------|
| `ESC` | Quit the application |
| `s` | Save current frame's lane point cloud as `lane_cloud_manual_NNNN.pcd` |

---

## Coordinate System

The world coordinate system is defined as:

- **Origin** — the point on the ground directly below the camera
- **X axis** — lateral (positive = camera right)
- **Y axis** — longitudinal (positive = forward / away from camera)
- **Z axis** — vertical (positive = up); always `0.0` for ground-projected points

The BEV image is oriented so that **forward is up** in the output image and the camera position is at the **bottom center**.
