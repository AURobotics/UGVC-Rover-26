# lane_detector_pkg

This package contains a classical lane and obstacle detection pipeline for the rover.

## `lane_classic.py`

`lane_classic.py` implements the `RoadFeatureDetector` class, which is responsible for:

- building a bird's-eye view (BEV) homography through `HomographyBEV`
- detecting lane markings using color filtering and edge extraction
- extracting lane line segments using the probabilistic Hough transform
- grouping segments into left and right lanes, fitting each lane line in image space
- projecting lane lines from image coordinates onto the ground plane in meters
- detecting circular potholes using Hough circle detection and contour analysis
- mapping detected potholes into ground coordinates and estimating their radius in meters
- computing lateral offsets relative to the camera center, both for lanes and for the open lane gap between detected potholes
- offering standalone debug helpers such as `process()`, `offsetx_lane()`, and `get_total_offset()`

Key methods:

- `detect_edges(frame)`: smooths the frame, thresholds white lane colors, and thins edges
- `detect_lines(edges)`: finds line segments with `cv2.HoughLinesP`
- `_fit_left_right_lanes(lines)`: separates lines by slope and fits one line per lane side
- `lane_to_ground_line(fit, height)`: converts a fitted lane model to two ground-plane points
- `detect_circles(image, white_mask)`: detects circular features in the white mask and validates them by shape
- `circle_to_ground(circle)`: converts a detected circle center to ground-plane coordinates
- `offsetx_lane(frame)`: estimates lateral lane center offset in meters
- `offsetx_circle(frame, circles, x_left_px, x_right_px, y_eval)`: computes potholes-avoidance offset inside the current lane corridor

## `homography.py`

`homography.py` defines `HomographyBEV`, which builds the camera-to-ground mapping needed for metric measurements.

The class handles:

- camera intrinsic matrix `K` and optional lens distortion correction
- camera pose parameters: height, pitch, yaw, and roll
- construction of the camera extrinsic rotation and translation matrices
- building the planar homography `H` that maps ground-plane points to image pixels
- computing the inverse homography `H_inv` to map image pixels back onto the ground plane
- creating a BEV warp matrix `H_bev` that transforms images into a top-down view
- generating a scaled BEV output image and point cloud from a binary mask

Important methods:

- `pixel_to_ground(u, v)`: undistorts a pixel and returns the corresponding ground-plane X,Y coordinates
- `pixels_to_ground(pixels)`: batch version for many points
- `mask_to_pointcloud(mask)`: converts a binary mask into a 3D ground-plane point cloud
- `warp_to_bev(image)`: warps an image into bird's-eye view using the BEV homography

## How they work together

`RoadFeatureDetector` uses `HomographyBEV` to convert detected lane and obstacle features from image coordinates into real-world distances and positions. This enables the rover to estimate lane geometry and obstacle offsets in meters rather than pixels.
