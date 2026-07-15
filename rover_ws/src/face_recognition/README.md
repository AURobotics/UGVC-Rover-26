# face_recognition ROS Package

## Overview

This package contains a ROS2 face recognition demo using OpenCV and `cv_bridge`.

- `face_recognition_node.py`
  - Main ROS2 node for face recognition
  - Subscribes to `/camera/image_raw`
  - Converts incoming ROS `sensor_msgs/Image` to OpenCV using `CvBridge`
  - Calls `FaceRecognition.recognize_frame()`
  - Publishes recognition outputs and displays the annotated result

- `test1_node.py`
  - Test/demo node that captures webcam frames with OpenCV (`cv2.VideoCapture(0)`)
  - Converts frames to ROS images with `CvBridge`
  - Publishes to `/camera/image_raw` at ~30 FPS and displays `/face_recognition/result_image`
  - Intended as a simple test input source for local development

- `test2_node.py`
  - Session-driven helper that subscribes to camera, result image, and `/face_recognition/offset`
  - Starts a 45-second tracking session and auto-stops when the face becomes centered
  - Useful for automated/manual testing of tracking behavior

- `cv_code/face_recognition.py`
  - Loads the YuNet face detector and SFace recognizer
  - Builds a target face feature vector from `assets/target.jpg`
  - Detects faces in each frame, extracts embeddings, and compares them to the target
  - Draws a bounding box and label for each detected face

## Package structure

- `face_recognition_node.py`
- `test1_node.py`
- `test2_node.py`
- `launch/face_recognition_launch.py`
- `cv_code/face_recognition.py`
- `cv_code/face_detection_yunet_2023mar.onnx`
- `cv_code/face_recognition_sface_2021dec.onnx`
- `cv_code/target_feature.npy`
- `cv_code/assets/target.jpg` (expected by the code)

## Required models

Before running the package, download the ONNX model files from the official GitHub releases for the OpenCV face recognition models.

Required model files:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`

Put these files in the `cv_code` folder inside the ROS package:

```text
UGVC-Rover-26/rover_ws/src/face_recognition/face_recognition/cv_code/
```

The final paths should be:

- `UGVC-Rover-26/rover_ws/src/face_recognition/face_recognition/cv_code/face_detection_yunet_2023mar.onnx`
- `UGVC-Rover-26/rover_ws/src/face_recognition/face_recognition/cv_code/face_recognition_sface_2021dec.onnx`

If you download files with different names, rename them to the exact names above or update the code in `cv_code/face_recognition.py`.

## Dependencies

This package requires:

- ROS2 Python support:
  - `rclpy`
  - `sensor_msgs`
  - `cv_bridge`
- OpenCV Python:
  - `opencv-contrib-python`

Also add these runtime dependencies to `package.xml`:

- `rclpy`
- `sensor_msgs`
- `cv_bridge`

## How it works

1. `test1_node.py` (camera publisher)

- Creates a ROS2 node that opens the webcam, converts frames to ROS `Image`, publishes to `/camera/image_raw`, and displays result images.
- Use this node as the simple test input source for local development.

2. `test2_node.py` (session helper)

- Subscribes to `/camera/image_raw`, `/face_recognition/result_image`, and `/face_recognition/offset`.
- Starts a timed tracking session and auto-stops when the face becomes centered within a configurable threshold.

2. `face_recognition_node.py`
   - Creates a ROS2 node `face_recognition`
   - Subscribes to `/camera/image_raw`
   - Converts ROS `Image` back to OpenCV BGR image
   - Runs face detection and recognition
   - Publishes recognition outputs
   - Shows the annotated result in an OpenCV window

3. `cv_code/face_recognition.py`
   - Loads ONNX models for detection and recognition
   - Uses `cv2.FaceDetectorYN` and `cv2.FaceRecognizerSF`
   - If `target_feature.npy` exists, loads it
   - Otherwise reads `./assets/target.jpg`, extracts the target face, computes its feature, and caches it

## Output topics and message types

The main recognition node publishes the following topics:

- `/face_recognition/result_image`
  - message type: `sensor_msgs/Image`
  - content: annotated camera frame with face box, label, and score

- `/face_recognition/is_faces`
  - message type: `std_msgs/Bool`
  - content: `true` if any face is detected in the frame, otherwise `false`

- `/face_recognition/is_detected`
  - message type: `std_msgs/Bool`
  - content: `true` if the target face is recognized, otherwise `false`

- `/face_recognition/offset`
  - message type: `std_msgs/Int32`
  - content: horizontal pixel offset from image center to the detected target face center
  - note: this is published only when the target face is detected and contains one integer value
  - positive offset means the target is to the right of center, negative means left of center

The camera test node publishes:

- `/camera/image_raw`
  - message type: `sensor_msgs/Image`
  - content: raw webcam frames for the recognition node to consume

## Offset (percentage) calculation

The recognition node publishes an `offset` message containing horizontal and vertical offsets expressed as percentages relative to the image center. Calculation used by the code:

- face center: `face_center_x = x + w / 2`, `face_center_y = y + h / 2`
- pixel offset from center: `offset_x_px = face_center_x - frame_width / 2`, `offset_y_px = face_center_y - frame_height / 2`
- percentage offset (relative to half the frame):
  - `offset_x_pct = offset_x_px / (frame_width / 2) * 100`
  - `offset_y_pct = offset_y_px / (frame_height / 2) * 100`

Interpretation:

- `0%` means perfectly centered on that axis
- Positive X → target is to the right, negative X → left
- Positive Y → target is below center, negative Y → above

If you prefer a percentage of the full frame instead of half-frame normalization, use `face_center_x / frame_width * 100` and `face_center_y / frame_height * 100`.

## Test nodes and helper utilities

This package includes simple test utilities to exercise the recognition pipeline and demonstrate output topics:

- `test1_node.py` — a camera publisher + simple result subscriber and display. It publishes `/camera/image_raw` and shows `/face_recognition/result_image` in a window. It also prints received offsets.
- `test2_node.py` — a session-driven helper that subscribes to camera, result image, and `/face_recognition/offset`, starts a 45-second tracking session, and auto-stops when the face becomes centered (within a configurable percent threshold).

Both test nodes are registered as console scripts by `setup.py` and can be run through ROS2 (or directly with Python for debugging).

## Run each node separately

You can run nodes either with the provided `launch` or individually. Replace `python3` with `python` on Windows if needed and ensure your environment is sourced.

Run using ROS2 entry points (recommended after `colcon build` and sourcing):

```bash
# From rover_ws
colcon build
source install/setup.bash   # Linux
call install\setup.bat     # Windows (PowerShell: .\install\setup.ps1)

# Run the main recognition node
ros2 run face_recognition face_recognition_node

# Run test utilities
ros2 run face_recognition test1_node
ros2 run face_recognition test2_node
```

Run files directly (quick local debug — makes it easier to use the notebook/camera on the machine):

```bash
cd rover_ws/src/face_recognition/face_recognition
python3 face_recognition_node.py
python3 test1_node.py
python3 test2_node.py
```

Keyboard controls in the test nodes:

- `test1_node.py` opens an OpenCV window and uses keyboard input to control the service: press `s` to start face recognition, `x` to stop it, and `Esc` to quit.
- `test2_node.py` uses `s` to start a 45-second session and `Esc` to quit.

Notes about other nodes:

- Use `test1_node.py` as the recommended test camera publisher; `camera_publisher_node.py` has been removed from this package.

## What `face_recognition_node` does (detailed)

`face_recognition_node` is the central processing node for the package. Key behaviors:

- Initialization
  - Creates a `CvBridge` instance and a `FaceRecognition` helper that loads the YuNet detector and SFace recognizer (ONNX models are required in `cv_code/`).
  - Creates publishers:
    - `/face_recognition/result_image` (`sensor_msgs/Image`): annotated frames with bounding boxes and labels
    - `/face_recognition/offset` (`geometry_msgs/Point`): offset.x and offset.y carry percentage offsets
  - Creates a service `/face_recognition/start` (`std_srvs/SetBool`) to enable/disable processing
  - Subscribes to `/camera/image_raw` (`sensor_msgs/Image`) to receive camera frames

- Runtime
  - When the `/face_recognition/start` service is called with `data=true`, the node processes incoming frames; with `false`, it stops processing but remains alive.
  - For each processed frame it:
    1. Runs face detection and recognition via `FaceRecognition.recognize_frame()`.
    2. Draws bounding boxes and confidence labels on the frame and publishes it to `/face_recognition/result_image`.
    3. Computes and publishes a two-axis percentage offset `(x, y)` as a `geometry_msgs/Point` to `/face_recognition/offset` when the target face is detected.
    4. If no faces or no target detected, the node publishes sentinel offsets to indicate the state (see source printing for exact sentinels).

- Output / Integration
  - Any other node can subscribe to `/face_recognition/offset` to steer actuators, pan/tilt cameras, or trigger higher-level behaviors based on the face position.
  - The node emits log messages to stdout with detection status and offsets for debugging.

## Troubleshooting

- If offsets are unexpectedly large (e.g. >100%), confirm you are reading percentage values and not pixel offsets; the node publishes percentage values by default.
- If the node prints `offset is None` or does not publish offsets, ensure the recognition service was started (`/face_recognition/start`) and that models exist in `cv_code/`.
- On Windows, `cv_bridge` binaries are sometimes unavailable; consider using a ROS-enabled Python environment or building `vision_opencv` from source.

---

If you want, I can also update `cv_code/face_recognition_cv.py` to expose an explicit `get_offset_percent()` helper and ensure the node always returns both X and Y percentages — shall I implement that now?
