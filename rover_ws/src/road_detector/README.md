# Table of Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Architecture](#architecture)
- [Dependencies](#dependencies)
- [Running Launch files](#running-launch-files)
  - [Default Run](#default-run)
  - [Debug \& Visualization](#debug--visualization)
- [Performance Monitoring](#performance-monitoring)
- [Nodes](#nodes)
  - [road detector node (MAIN NODE)](#road-detector-node-main-node)
    - [Topics](#topics)
      - [Subscribed](#subscribed)
      - [Published](#published)
    - [Parameters](#parameters)
      - [Topic Parameters](#topic-parameters)
      - [Camera Extrinsic Parameters](#camera-extrinsic-parameters)
      - [Camera Intrinsic Parameters](#camera-intrinsic-parameters)
    - [Detection Parameters](#detection-parameters)
    - [Debug / Output Parameters](#debug--output-parameters)
      - [Dynamic Parameter Updates](#dynamic-parameter-updates)
  - [video publisher node (TESTING)](#video-publisher-node-testing)
  - [point cloud logger node (TESTING)](#point-cloud-logger-node-testing)
  - [Viewer Node (TESTING)](#viewer-node-testing)

---

# Overview

The `road_detector` node subscribes to a camera image stream, processes each frame through a Bird's Eye View (BEV) pipeline, and publishes detected road features — lane markings and potholes — as `PointCloud2` messages in 3D space.

Key capabilities:

- Lane marking detection with configurable radius bounds
- Pothole/circle detection projected into 3D via BEV homography
- Camera intrinsic and extrinsic calibration support
- Optional debug image publishing (lane mask, BEV view)
- Optional performance statistics publishing
- Dynamic parameter updates at runtime (no restart required)
- Lazy pipeline initialization — adapts to actual incoming image resolution

---

# Architecture

```
/camera/image_raw  ──►  RoadDetectorNode
                              │
                    ┌─────────▼──────────┐
                    │  RoadFeatureBEV    │
                    │  Pipeline          │
                    │  (BEV transform +  │
                    │   lane detection)  │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       /road_detector   lane_mask img    bev_image img
        /pointcloud      (debug)          (debug)
```

The pipeline is initialized lazily on the first received frame, so image resolution does not need to be hardcoded — it is read from the first incoming message.

---

# Dependencies

| Dependency       | Purpose                                                   |
| ---------------- | --------------------------------------------------------- |
| `sensor_msgs`    | `Image`, `PointCloud2`, `CameraInfo` message types        |
| `std_msgs`       | `String` for stats                                        |
| `cv_bridge`      | ROS ↔ OpenCV image conversion                             |
| `OpenCV`         | Image processing                                          |
| `numpy`          | Numerical operations                                      |
| `sensor_msgs_py` | `point_cloud2` helper for building `PointCloud2` messages |

Internal modules (within the package):

- `cv_code.road_features_detector` — `RoadFeatureDetector` class
- `cv_code.pipeline` — `RoadFeatureBEVPipeline` class


---

# Running Launch files

## Default Run

run main launch file
```bash
ros2 launch road_detector road_detector_launch.py
```

>depends on params.yaml (**road detector node only**)

---

## Debug & Visualization

run test launch file
```bash
ros2 launch road_detector road_detector_test_launch.py
```

>depends on all other three yaml files (depends on all nodes)

it will view 2 debug camera feeds (bev and lane mask) and the raw camera feed as windows
+
data from point cloud topic is saved in a file specified in the config/ parameter files

---

# Performance Monitoring

When `publish_performance_stats` is `true`, the node publishes a string to `/road_detector/stats` after every frame:

```
Frame: 250, Processing: 18.43ms, Avg: 19.12ms ± 1.34ms, FPS: 52.3
```

Monitor live:

```bash
ros2 topic echo /road_detector/stats
```

The node also logs a summary to the ROS logger every 100 frames.

Statistics are computed over a rolling window of the last 30 frames.

---

# Nodes

## road detector node (MAIN NODE)

The core processing node. Subscribes to a camera stream, runs each frame through the BEV pipeline, and publishes lane points and pothole detections as `PointCloud2` messages.

**Executable:** `road_detector_node`

### Topics

#### Subscribed

| Topic               | Type                | QoS                            | Description         |
| ------------------- | ------------------- | ------------------------------ | ------------------- |
| `/camera/image_raw` | `sensor_msgs/Image` | Best Effort, Volatile, depth 1 | Input camera stream |

> **Important:** The camera subscription uses `BEST_EFFORT` QoS to match typical camera driver publishers. Any subscriber or tool connecting to this topic must use a compatible (`BEST_EFFORT`) QoS profile, otherwise no data will flow and no error will be raised.

#### Published

| Topic                            | Type                      | QoS                | Description                        |
| -------------------------------- | ------------------------- | ------------------ | ---------------------------------- |
| `/road_detector/pointcloud`      | `sensor_msgs/PointCloud2` | Reliable, depth 10 | 3D lane marking and pothole points |
| `/road_detector/debug/lane_mask` | `sensor_msgs/Image`       | Reliable, depth 10 | Debug: lane detection overlay      |
| `/road_detector/debug/bev_image` | `sensor_msgs/Image`       | Reliable, depth 10 | Debug: Bird's Eye View transform   |
| `/road_detector/stats`           | `std_msgs/String`         | Reliable, depth 10 | Processing performance stats       |

Debug image topics are always advertised. Data is only published on them when `publish_debug_images` is `true`. Stats topic is only published when `publish_performance_stats` is `true`.

---

### Parameters

#### Topic Parameters

| Parameter                 | Default                          | Description                                           |
| ------------------------- | -------------------------------- | ----------------------------------------------------- |
| `camera_topic`            | `/camera/image_raw`              | Input image topic                                     |
| `camera_info_topic`       | `/camera/camera_info`            | Camera info topic (declared, not actively subscribed) |
| `output_pointcloud_topic` | `/road_detector/pointcloud`      | Output point cloud topic                              |
| `output_lane_mask_topic`  | `/road_detector/debug/lane_mask` | Lane mask debug image topic                           |
| `output_bev_topic`        | `/road_detector/debug/bev_image` | BEV debug image topic                                 |
| `output_stats_topic`      | `/road_detector/stats`           | Performance stats topic                               |

#### Camera Extrinsic Parameters

| Parameter       | Default | Description                                                                                           |
| --------------- | ------- | ----------------------------------------------------------------------------------------------------- |
| `camera_height` | `1.43`  | Height of camera above ground (metres). Must be > 0                                                   |
| `pitch_deg`     | `-50.0` | Camera pitch in degrees. Negative = pointing down toward road. Positive values will trigger a warning |

#### Camera Intrinsic Parameters

These form the camera matrix **K**:

```
K = [[fx,  0, cx],
     [ 0, fy, cy],
     [ 0,  0,  1]]
```

| Parameter | Default  | Description                          |
| --------- | -------- | ------------------------------------ |
| `fx`      | `1000.0` | Focal length X (pixels). Must be > 0 |
| `fy`      | `1000.0` | Focal length Y (pixels). Must be > 0 |
| `cx`      | `960.0`  | Principal point X (pixels)           |
| `cy`      | `540.0`  | Principal point Y (pixels)           |

### Detection Parameters

| Parameter    | Default | Description                                                              |
| ------------ | ------- | ------------------------------------------------------------------------ |
| `min_radius` | `10`    | Minimum circle/pothole detection radius (pixels). Must be < `max_radius` |
| `max_radius` | `200`   | Maximum circle/pothole detection radius (pixels)                         |

### Debug / Output Parameters

| Parameter                   | Default | Description                                        |
| --------------------------- | ------- | -------------------------------------------------- |
| `publish_debug_images`      | `false` | Publish lane mask and BEV images                   |
| `publish_performance_stats` | `false` | Publish per-frame processing time stats            |
| `max_points_per_cloud`      | `10000` | Maximum points per published `PointCloud2` message |

#### Dynamic Parameter Updates

The following parameters can be updated at runtime without restarting the node:

```bash
ros2 param set /road_detector publish_debug_images true
ros2 param set /road_detector min_radius 15
ros2 param set /road_detector max_radius 150
ros2 param set /road_detector publish_performance_stats true
```

**Behaviour notes:**

- The pipeline (`RoadFeatureBEVPipeline`) is initialized lazily on the first received frame using the actual image dimensions — no hardcoded resolution required.
- Lane points and per-circle pothole clouds are all published to the same `/road_detector/pointcloud` topic as separate messages per frame.
- Points exceeding `max_points_per_cloud` are truncated (first N kept). NaN/Inf points are filtered before publishing.
- Debug image topics are always advertised regardless of `publish_debug_images`; data only flows when the flag is `true`.
- A rolling error counter (`consecutive_error_counter`) tracks pipeline failures and resets to 0 on any successful frame.
- Performance stats are computed over a rolling window of the last 30 frames and published after every frame when `publish_performance_stats` is `true`.

**Params file:** `config/params.yaml`

---

## video publisher node (TESTING)

Publishes a pre-recorded video file as a ROS2 image stream, simulating a live camera. Useful for offline testing and reproducible benchmarking without physical hardware.

**Executable:** `video_publisher_node`

**Params file:** `config/video_publisher_params.yaml`

---

## point cloud logger node (TESTING)

Subscribes to the road detector's point cloud output and saves it to disk. Used in the test/debug launch to record detection results for offline analysis.

**Executable:** `point_cloud_logger_node`

**Params file:** `config/point_cloud_logger_params.yaml`

---

## Viewer Node (TESTING)

A lightweight OpenCV viewer is included for inspecting all three image streams simultaneously.

```python
# video_viewer_node.py
ros2 run road_detector video_viewer_node
```

Opens three separate windows:

| Window        | Topic                            | Description                |
| ------------- | -------------------------------- | -------------------------- |
| `Camera Feed` | `/camera/image_raw`              | Raw camera input           |
| `Lane Mask`   | `/road_detector/debug/lane_mask` | Lane detection result      |
| `BEV Image`   | `/road_detector/debug/bev_image` | Bird's Eye View projection |

> **QoS note:** The camera window subscribes with `BEST_EFFORT` QoS to match the camera publisher. The debug windows use the default `RELIABLE` QoS to match the detector's debug publishers. Mismatching these will result in a silently empty window with no errors.

---