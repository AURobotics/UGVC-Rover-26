# 🛰️ Rover Vision — Road Feature Detection & BEV Mapping

A real-time computer vision pipeline for autonomous rover competition, performing **lane detection**, **road marker recognition**, and **bird's-eye-view (BEV) ground projection** from a single monocular camera.

---

## Overview

This system takes a forward-facing camera feed and produces:

- Detected **lane lines** in pixel space and metric ground coordinates
- Detected **circular road markers** (e.g. roundabouts, stop circles) with real-world center and radius
- A **bird's-eye-view warp** of the scene for top-down situational awareness
- **3D point clouds** (`.pcd`) of lane lines and circle boundaries on the ground plane

---

## Architecture

```
Camera Frame
     │
     ▼
RoadFeatureDetector
     ├── detect_edges()      → White-line mask (HSV threshold + morphology + thinning)
     ├── detect_lines()      → Hough line segments (lane markings)
     └── _detect_circles()   → Hough circles + contour fallback (road markers)
     │
     ▼
HomographyBEV
     ├── pixel_to_ground()   → Single pixel → (X, Y) metric ground coords
     ├── pixels_to_ground()  → Batch pixel projection
     ├── mask_to_pointcloud()→ Full mask → (N, 3) XYZ point cloud
     └── warp_to_bev()       → Undistort + perspective warp to top-down view
     │
     ▼
RoadFeatureBEVPipeline
     ├── Lane point cloud    → (N, 3) float64 [X, Y, 0] in metres
     ├── Circle list         → [(X, Y, radius_m), ...]
     ├── Circle clouds       → [(N, 3), ...] ring/disc point clouds
     └── BEV image           → Warped top-down BGR frame
```

---

## Modules

| File | Description |
|---|---|
| `homography.py` | Camera model, homography computation, lens undistortion, ground projection, BEV warping, PCD export |
| `road_features_detector.py` | Lane and circle detection pipeline on raw frames |
| `pipeline.py` | End-to-end orchestration; outputs annotated frames, BEV, and point clouds |

---

## Setup

### Requirements

```bash
pip install opencv-python opencv-contrib-python numpy
```

> `opencv-contrib-python` is required for `cv2.ximgproc.thinning` (skeletonisation of lane masks).

### Folder Structure

```
project/
├── data/
│   └── raw/
│       ├── test_lane.mp4
│       └── ground.jpeg
├── homography.py
├── road_features_detector.py
└── pipeline.py
```

---

## Camera Calibration

The pipeline requires intrinsic camera parameters. Provide the **3×3 intrinsic matrix K**:

```python
K = np.array([
    [fx,  0, cx],
    [ 0, fy, cy],
    [ 0,  0,  1]
], dtype=np.float64)
```

Optionally provide a **distortion coefficient vector** (OpenCV 5-parameter model):

```python
dist_coeffs = np.array([k1, k2, p1, p2, k3])
```

If omitted, distortion is assumed to be zero. When provided, lens undistortion is applied automatically before every projection and BEV warp.

And the camera **mounting parameters**:

| Parameter | Description |
|---|---|
| `camera_height` | Height of camera above ground plane (metres) |
| `pitch_deg` | Camera pitch angle (degrees, negative = downward tilt) |
| `yaw_deg` | Camera yaw angle (degrees, positive = rotated right). Default `0.0` |
| `roll_deg` | Camera roll angle (degrees, positive = tilted right). Default `0.0` |

Example values used in competition testing:

```python
camera_height = 1.33   # metres
pitch_deg     = -45    # degrees
yaw_deg       = -2     # degrees — small left offset from mount
roll_deg      = -7     # degrees — slight sideways tilt
```

### Rotation Convention

The full world-to-camera rotation is composed as:

```
R = M · R_pitch · R_yaw · R_roll
```

where `M = diag(-1, 1, 1)` mirrors the X axis so that +X is rightward in the image. Each angle has an independent, physically meaningful effect:

| Angle | Axis | Effect |
|---|---|---|
| `pitch_deg` | X | Tilts camera up/down — primary mounting angle |
| `yaw_deg` | Z | Rotates camera left/right relative to rover heading |
| `roll_deg` | Y | Tilts camera sideways — corrects lateral mounting error |

For a perfectly aligned camera only `pitch_deg` is non-zero. In practice, small yaw/roll corrections (±2–7°) compensate for mounting tolerances that would otherwise produce a skewed BEV.

---

## Usage

### Run the full pipeline on a video

```bash
python pipeline.py
```

This opens a video feed and displays three windows:

- **Road Features** — annotated frame with detected lanes and circles
- **Lane Mask** — binary mask of detected lane lines
- **BEV** — bird's-eye-view warp of the current frame

### Keyboard Controls

| Key | Action |
|---|---|
| `ESC` | Quit |
| `s` | Save current frame's lane point cloud as `.pcd` |

On exit, the full merged lane point cloud across all frames is saved to `lane_cloud_full.pcd`.

### Run homography standalone (single image)

```bash
python homography.py
```

Loads `data/raw/ground.jpeg`, projects a pixel to metric ground, warps to BEV, generates a point cloud from a thresholded mask, and saves `ground_plane.pcd`.

---

## Outputs

### Point Cloud (`.pcd`)

Ground-plane point clouds are saved in **PCD ASCII format** compatible with CloudCompare, Open3D, and ROS:

```
FIELDS x y z
TYPE F F F
DATA ascii
```

Each point is a 3D position `(X, Y, 0)` in the rover's ground coordinate frame, where:

- **X** — lateral axis (left/right)
- **Y** — forward axis (depth from rover)
- **Z** — always 0 (ground plane)

### Circle Detection Output

Each detected circle is reported as:

```
center = (X, Y)   # metric ground position in metres
radius = r        # estimated real-world radius in metres
```

---

## Coordinate Frame

```
         ▲ Y (forward)
         │
         │
 ────────┼────────▶ X (right)
         │
    Camera/Rover origin
```

The ground plane is `Z = 0`. All projections assume a flat ground surface.

---

## Tuning

Key parameters to adjust for different environments:

| Parameter | Location | Effect |
|---|---|---|
| `lower_white` / `upper_white` | `RoadFeatureDetector.__init__` | HSV range for white line detection |
| `min_radius` / `max_radius` | `RoadFeatureDetector.__init__` | Circle size filter (pixels) |
| Hough `threshold`, `minLineLength`, `maxLineGap` | `detect_lines()` | Lane line sensitivity |
| `circularity` threshold (0.6) | `_detect_circles()` | Roundness filter for contour fallback |
| `white_ratio` threshold (0.35) | `_detect_circles()` | Minimum white fill inside detected circle |
| `yaw_deg` / `roll_deg` | `HomographyBEV.__init__` | Fine-tune mounting misalignment; adjust until BEV lanes appear straight and parallel |

---

## Competition Notes

- The pipeline runs **frame-by-frame** with no temporal filtering — adding a Kalman filter or frame-to-frame tracking would improve stability.
- BEV warping assumes a **flat, level ground plane**. Uneven terrain will introduce projection errors.
- Point clouds accumulate across frames (`all_points` list in `pipeline.py`) and are merged on exit — useful for building a local map of the course.
- For real-time performance, consider downscaling input frames before processing.
- Lens undistortion is applied on every frame and every pixel projection. If `dist_coeffs` are inaccurate, straight lines will appear curved in the BEV — re-run calibration with a checkerboard to obtain reliable coefficients.
