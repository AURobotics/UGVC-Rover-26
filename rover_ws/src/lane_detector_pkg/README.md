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

## `errors_percentage.py`

`ObstacleDetector` is the main perception node responsible for detecting lanes , obstacles and circular holes from the camera stream. it combines classical computer vision with YOLO model to estimate the safest direction for rover and publish navigation errors for control nodes.

The node performs the following tasks : 
- Detect lane boundaries using classic image processing(`get_lane_data`) for `RoadFeatureDetector` class
- Detect obstacles using trained YOLO model(`ModelForObstacle.pt`)
- Detect circular holes on the road for `RoadFeatureDetector`
- Compute lane error(`lane/error`)
- Compute obstacle errror(`obstacle/errot`)
- Compute circular holes error(`circle/error`)
- Compute final error based on largest free space inside the lane
- Publish a visualization image for debugging

`Navigation Error Calculations`
after indentifying all obstacles and lane boundaries , the algorithm computes the `lagerst free gap` inside the lane . the rover is guided the center of that gap 
- The center of the selected gap calculated as : 
`target center = (Gap Start + Gap End) / 2​`
- The camera center calculated as :
`frame center = image width / 2`
- The navigation error calculated as :
`total error = target center - frame center`
- The published error calculated as : 
`published error = (total error / frame center) * 54`
- -54<= published error <=54
positive values -> steer right
negative values -> steer left
- The normalized error is multiplied by 54 to map it back to the camera image coordinates, where the image width is 108 pixels and the center is located at x = 54 pixels

- `Subcribes Topic`
 - `camera/image/raw` : receives
 the live camera image
  `reasons` : 
   - used as main input for lane detection
   - performs YOLO obstacle model 
   - detect circular holes

- `Published Topics`
 - `camera/publish` : publish the processed image after drawing :
  - detect lanes 
  - obstacles
  - circles
  - target center 
  - frame center 
  `reasons` :
   - used for debugging
 - `lane/error` : publish the lane center error 
  `reasons` : 
   - allow the controller to keep the rover between lanes 
 - `obstacle/error` : publish the steering error to avoid the detected obstacles
  `reasons` : 
   - provides the controller with  the safest direction around obstacles 
 - `obstacle/detected` : indicate whether any obstacle exists inside the lane 
  `reasons` : 
   - allows other nodes to know when obstacle avoidance should become active
 - `circle/error` : publish the steering error to avoid the circular holes
  `reasons` : 
    - provides the controller with  the safest direction around circular holes 
 - `circle/detected` : indicate whether any obstacle exists inside the lane 
  `reasons` : 
    - allows other nodes to know  when circular holes should become active
 - `total/error` : publish the final navigation error
  `reasons` : 
   - represents the final navigation error after combining lane error , obstacle error and circle error

- `Services` 
 - `/obstacle_detector/start` : start and stop the obstacle detector
 when the service receives :
 `true` -> detection start 
 `false` -> detection stop
  `reasons` :
   - Allows external nodes to enable or disable perception during different mission stages

## `lanes_obstacles_error.py`

this node performs the same perception pipline as the previous implemention, including : 
- lane detection
- obstacle detection using YOLO model
- circular holes detection 
- safe gap calculation
- navigation error calculation

`difference between error_percentage.py`
- lane error is published in meters instead pixels using BEV homography
- obstacle error is computed in meters using BEV homography
- total navigation error represents the rover's lateral distance in meteres 

## `Testing`
The node was tested in both simulations and real-world scenarios

## `another unused model`
`ModelForLanes.pt` : trained YOLO model to detect lanes and make boxes about lanes after that follow the same previous algorithms

`ModelForHoles.pt` : trained YOLO model to detect circular holes and make boxes about circles after that follow the same previous algorithms

`how to get the data` : collect the data from vedios similar to the competion and another self driving vedios after that train the models on google colab






