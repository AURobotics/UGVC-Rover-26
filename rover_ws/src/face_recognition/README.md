# Face Recognition ROS Package

## What this package does

This package provides a simple ROS 2 face-recognition demo for the rover. It reads images from a camera topic, detects faces in each frame, compares them to a reference face, and publishes the annotated result plus a position offset for tracking.

The core flow is:

1. A camera node publishes frames to `/camera/image_raw`.
2. The main recognition node reads those frames.
3. OpenCV detects faces and extracts facial features.
4. The features are compared to the reference face from `assets/target.jpg`.
5. The node publishes an annotated image and an offset that can be used by other rover nodes.

## Package layout

- `face_recognition/face_recognition_node.py` — main ROS 2 node
- `face_recognition/test1_node.py` — webcam publisher and simple user interface
- `face_recognition/test2_node.py` — optional session-based helper node
- `launch/face_recognition_launch.py` — launch file for a quick demo
- `face_recognition/cv_code/face_recognition_cv.py` — the computer-vision logic
- `face_recognition/cv_code/assets/target.jpg` — reference image used to build the target face embedding

## The CV code explained

The computer-vision logic lives in `face_recognition/cv_code/face_recognition_cv.py`. This file is the heart of the package because it turns raw camera frames into useful detection results.

### 1. What the code is doing at a high level

The script follows a very simple pipeline:

1. Read a frame from the camera.
2. Detect faces in that frame.
3. For each detected face, extract a compact face signature.
4. Compare that signature with the signature of the reference face.
5. Draw the result on the image and return whether the target was found.

In other words, it does two main jobs:

- detect where faces are in the image
- decide whether a detected face looks like the reference face you chose

### 2. Model loading

The class `FaceRecognition` loads two different OpenCV models when it starts:

- `face_detection_yunet_2023mar.onnx` — the detector
  - This model scans the image and finds face locations.
  - It returns bounding boxes for each detected face.

- `face_recognition_sface_2021dec.onnx` — the recognizer
  - This model does not just say “there is a face.”
  - It extracts a feature vector that describes the face in a compact way.
  - That feature vector is then compared with the feature vector of the target face.

These models are loaded from the `cv_code` folder and are required before the node can run.

### 3. How the target face is created

To recognize a specific person, the code needs a reference face.

When the program starts, it checks whether a cache file named `target_feature.npy` already exists. If it does, the code loads that saved feature directly. If not, it:

- reads `assets/target.jpg`
- runs face detection on that image
- crops the detected face
- extracts its feature vector
- saves the vector to `target_feature.npy`

This is important because the recognition step compares every detected face against this stored reference. The cache avoids recomputing the same feature every time the package starts.

### 4. How each frame is processed

Inside `recognize_frame()`, the code follows this sequence:

1. Set the detector input size to match the current frame size.
2. Run the detector and get a list of detected faces.
3. For each detected face:
   - align and crop the face region
   - compute a feature vector for that face
   - compare it with the target feature using cosine similarity
4. Decide whether the result is a match or an unknown face.
5. Draw a rectangle and label on the image.
6. Return the processed image and the detection result.

The matching step is based on similarity score. In this code, a score above `0.45` is treated as a match. That threshold can be tuned if you want the system to be stricter or more permissive.

### 5. Why the code draws boxes and labels

The drawing step is not just for visualization. It makes the output easy to understand when you run the node locally:

- green boxes mean the detected face matched the target
- red boxes mean a face was detected but did not match the target
- text above the box shows the label and confidence-like score

This makes it much easier to debug whether the detector is working and whether the recognizer is behaving correctly.

### 6. How the offset works

The code also computes a position offset for the detected face. This is useful for tracking or steering.

The offset is calculated from the center of the detected face:

- the face center is computed from its box coordinates
- the image center is computed from the frame size
- the difference between the two is converted into percentages

So the output tells you roughly:

- how far the face is from the middle of the frame
- whether it is to the left or right
- whether it is above or below the center

This is why the node can publish a meaningful movement signal to other rover components.

### 7. Why this design is useful for ROS

The CV code itself is independent of ROS, but the ROS node wraps it into a real pipeline:

- the node receives images from a camera topic
- the CV logic processes them
- the result is published as an image and offset message

That separation makes the code easier to understand and easier to reuse in different projects.

## Models you need

Download these files and place them in the package folder:

```text
rover_ws/src/face_recognition/face_recognition/cv_code/
```

Required files:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`

The code expects those exact file names. If you rename them, update the paths in `face_recognition_cv.py`.

## Dependencies

Install the Python dependencies in the environment you use for ROS:

```bash
python3 -m pip install opencv-contrib-python
```

You will also need the normal ROS 2 Python dependencies such as:

- `rclpy`
- `sensor_msgs`
- `cv_bridge`

## Quick start

### 1. Build the workspace

From the repository root:

```bash
cd rover_ws
colcon build --packages-select face_recognition
```

### 2. Source the environment

On Linux/macOS:

```bash
source install/setup.bash
```

On Windows PowerShell:

```powershell
.\install\setup.ps1
```

### 3. Run the package

The easiest way is to use the launch file:

```bash
ros2 launch face_recognition face_recognition_launch.py
```

This starts:

- `test1_node` — publishes webcam frames and shows the annotated output
- `face_recognition_node` — processes the input and publishes the result topics

### 4. Start recognition

The recognition node waits for the start service. You can start it with:

```bash
ros2 service call /face_recognition/start std_srvs/srv/SetBool "{data: true}"
```

You can also use the keyboard controls in the test window:

- `s` — start face recognition
- `x` — stop face recognition
- `Esc` — quit

## Running nodes individually

If you want to run them manually:

```bash
ros2 run face_recognition test1_node
ros2 run face_recognition face_recognition_node
```

You can also launch the optional helper session node:

```bash
ros2 run face_recognition test2_node
```

## How the main face recognition node works

The main node is implemented in `face_recognition/face_recognition_node.py`. It acts as the bridge between the computer-vision code and ROS 2.

### What it does

1. It creates a ROS 2 node named `face_recognition_node`.
2. It creates a `CvBridge` object so it can convert between ROS `Image` messages and OpenCV images.
3. It initializes the `FaceRecognition` class from the CV file.
4. It subscribes to `/camera/image_raw` to receive video frames.
5. It publishes:
   - `/face_recognition/result_image` for the annotated output image
   - `/face_recognition/offset` for the face position feedback
6. It exposes a service `/face_recognition/start` using `std_srvs/SetBool`.

### Why the service exists

The node does not process frames continuously from the start. Instead, it waits for a service call.

When the service receives:

- `data: true` → the node starts processing incoming frames
- `data: false` → the node stops processing

This is useful because you may want to control the recognition pipeline from another node or from a simple test interface.

### What happens in the callback

When a camera image arrives, the node:

1. converts the ROS image into an OpenCV frame
2. passes the frame to `FaceRecognition.recognize_frame()`
3. gets back the processed frame, detection results, and offset values
4. publishes the result image and offset message

So the node is basically a wrapper that brings the CV logic into the ROS ecosystem.

## How the test node works

The test node is implemented in `face_recognition/test1_node.py`.

This node is meant to be a simple demonstration and debugging tool. It combines three jobs:

1. it opens the webcam
2. it publishes frames to `/camera/image_raw`
3. it shows the result image coming back from the recognition node

### What it does step by step

- It creates a ROS 2 node called `camera_publisher`.
- It opens the local webcam with OpenCV.
- It publishes each frame as a ROS `Image` message to `/camera/image_raw`.
- It subscribes to `/face_recognition/result_image` so it can display the annotated frame.
- It also subscribes to `/face_recognition/offset` so it can print the detected face position.

### Why this node is useful

This node gives you a complete mini-demo:

- the camera stream enters the system
- the recognition node processes it
- the final annotated image comes back
- you can see the detection behavior live

It is especially helpful when you are testing the package for the first time.

### Keyboard controls

In the test window you can press:

- `s` → start the recognition service
- `x` → stop the recognition service
- `Esc` → exit the demo

## How the service client works

The service client logic is inside `test1_node.py`.

It uses a ROS 2 client for the service `/face_recognition/start`.

### What the client does

When you press `s`, the node:

1. creates a `SetBool.Request`
2. sets `request.data = True`
3. sends the request to the recognition node
4. waits for the response

The recognition node replies with a success flag and a message such as:

- `Face recognition started`
- `Face recognition stopped`

### Why this pattern is useful

This is a clean way to control a node without restarting it. The test node can start or stop processing at any time, and the main recognition node remains alive the whole time.

In short:

- the test node acts as the input and display tool
- the recognition node performs the actual CV work
- the service client lets you turn the processing on and off remotely

## Troubleshooting

- If the node cannot find the model files, check that the `.onnx` files are in the `cv_code` folder with the exact expected names.
- If the camera does not open, verify that your webcam is available and that OpenCV can access it.
- If the node does not publish offsets, make sure the start service was activated.
- If you are on Windows and `cv_bridge` fails to import, use a ROS-enabled Python environment or rebuild the relevant ROS packages.

## Notes for learning the package

If you are new to this package, the best order to explore it is:

1. `face_recognition_cv.py` — understand the detection and recognition pipeline
2. `face_recognition_node.py` — see how the CV result becomes ROS topics
3. `test1_node.py` — see how the camera stream is published and displayed
4. `launch/face_recognition_launch.py` — see how the demo is launched end-to-end
