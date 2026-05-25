# face_recognition ROS Package

## Overview

This package contains a ROS2 face recognition demo using OpenCV and `cv_bridge`.

- `face_recognition_node.py`
  - Subscribes to `/camera/image_raw`
  - Converts incoming ROS `sensor_msgs/Image` to OpenCV using `CvBridge`
  - Calls `FaceRecognition.recognize_frame()`
  - Displays the annotated frame in an OpenCV window

- `camera_publisher_node.py`
  - Captures webcam frames with OpenCV (`cv2.VideoCapture(0)`)
  - Converts frames to ROS images with `CvBridge`
  - Publishes to `/camera/image_raw` at ~30 FPS

- `cv_code/face_recognition.py`
  - Loads the YuNet face detector and SFace recognizer
  - Builds a target face feature vector from `assets/target.jpg`
  - Detects faces in each frame, extracts embeddings, and compares them to the target
  - Draws a bounding box and label for each detected face

## Package structure

- `face_recognition_node.py`
- `camera_publisher_node.py`
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

1. `camera_publisher_node.py`
   - Creates a ROS2 node `camera_publisher`
   - Opens the webcam
   - Converts frames to ROS `Image`
   - Publishes to `/camera/image_raw`

2. `face_recognition_node.py`
   - Creates a ROS2 node `face_recognition`
   - Subscribes to `/camera/image_raw`
   - Converts ROS `Image` back to OpenCV BGR image
   - Runs face detection and recognition
   - Shows the result in an OpenCV window

3. `cv_code/face_recognition.py`
   - Loads ONNX models for detection and recognition
   - Uses `cv2.FaceDetectorYN` and `cv2.FaceRecognizerSF`
   - If `target_feature.npy` exists, loads it
   - Otherwise reads `./assets/target.jpg`, extracts the target face, computes its feature, and caches it

## Run instructions

### 1. Build your workspace

From `UGVC-Rover-26/rover_ws`:

```bash
colcon build
```

### 2. Source the workspace

Linux:

```bash
source install/setup.bash
```

Windows:

```powershell
call install\setup.bat
```

### 3. Launch the package with ROS2

```bash
ros2 launch face_recognition face_recognition_launch.py
```

This launch file starts both:

- `camera_publisher_node`
- `face_recognition_node`

### 4. Run nodes directly (optional)

If you prefer to run nodes without launch:

```bash
cd UGVC-Rover-26/rover_ws/src/face_recognition/face_recognition
python3 camera_publisher_node.py
python3 face_recognition_node.py
```

### 5. Notes

- Make sure the ONNX files are downloaded and placed in `cv_code/`.
- `target_feature.npy` is generated automatically from `cv_code/assets/target.jpg`.
- On Windows, `cv_bridge` may require building `vision_opencv` from source if a binary package is unavailable.
- If ROS imports fail, verify you are using the ROS2-enabled Python interpreter and that the workspace setup file is sourced.
