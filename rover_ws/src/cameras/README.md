# Dual USB Camera ROS 2 Package

A ROS 2 package that captures and displays video from two USB cameras simultaneously. Designed as a foundation for road detection and other computer vision pipelines.

---

## Package Structure

```
cameras/
├── launch/
|   └── launch.py # Launch file for both camera nodes (conatins parameters)
└── cameras/
    ├── camera_node.py # USB camera publisher node
    └── viewer_node.py # Dual-camera viewer node
```

---

## Nodes

### `camera_node.py` — `UsbCameraPublisher`

Opens a USB camera via OpenCV and publishes frames as ROS 2 `sensor_msgs/Image` messages.

**Parameters**

| Parameter      | Type   | Default               | Description                         |
| -------------- | ------ | --------------------- | ----------------------------------- |
| `device_index` | int    | `0`                   | Camera device index (`/dev/videoN`) |
| `publish_rate` | float  | `15.0`                | Publishing rate in Hz               |
| `frame_id`     | string | `"camera"`            | TF frame ID stamped on each message |
| `topic`        | string | `"/camera/image_raw"` | Topic to publish images on          |

**Published Topics**

| Topic                              | Type                | QoS                                        |
| ---------------------------------- | ------------------- | ------------------------------------------ |
| Configurable via `topic` parameter | `sensor_msgs/Image` | Best Effort, Volatile, Keep Last (depth 1) |

---

### `viewer_node.py` — `Viewer`

Subscribes to two camera topics and displays each feed in its own OpenCV window.

**Subscribed Topics**

| Topic                | Type                | QoS                                        |
| -------------------- | ------------------- | ------------------------------------------ |
| `/camera1/image_raw` | `sensor_msgs/Image` | Best Effort, Volatile, Keep Last (depth 1) |
| `/camera2/image_raw` | `sensor_msgs/Image` | Best Effort, Volatile, Keep Last (depth 1) |

---

## Launch File

`launch.py` starts two `camera_node` instances with the following configuration:

| Node name | `device_index` | `topic`              | `frame_id` |
| --------- | -------------- | -------------------- | ---------- |
| `camera1` | `0`            | `/camera1/image_raw` | `camera1`  |
| `camera2` | `2`            | `/camera2/image_raw` | `camera2`  |

Both nodes publish at **30 Hz**.

---

## Running

### Launch both cameras

```bash
ros2 launch cameras launch.py
```

### Run the viewer (TESTING)

```bash
ros2 run cameras viewer_node
```

### Run a single camera node manually

```bash
ros2 run cameras camera_node --ros-args \
  -p device_index:=0 \
  -p publish_rate:=30.0 \
  -p topic:=/camera1/image_raw \
  -p frame_id:=camera1
```

---

## Notes

- Camera indices map to `/dev/videoN` on Linux. Run `ls /dev/video*` to list available devices.
- Optimized QoS profile for efficient data transmission. Ensure subscribers use a compatible QoS profile.
- The viewer uses `passthrough` encoding when converting images, preserving the original color format published by the camera node (`bgr8`).

## IMPORTANT

**When subscribing to camera topics, you need to set the qos of the subscriber to match the publisher or else data will silently not get recieved**

qos by subscriber:

```python
qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
```
