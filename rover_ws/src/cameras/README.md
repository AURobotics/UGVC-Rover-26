# Dual USB Camera ROS 2 Package

A ROS 2 package that captures and displays video from USB connected cameras.

- [Dual USB Camera ROS 2 Package](#dual-usb-camera-ros-2-package)
  - [Package Structure](#package-structure)
  - [Nodes](#nodes)
    - [for both `external_camera_node.py` and `internal_camera_node.py`](#for-both-external_camera_nodepy-and-internal_camera_nodepy)
      - [Parameters](#parameters)
      - [QoS Profile](#qos-profile)
    - [`external_camera_node.py` speciality](#external_camera_nodepy-speciality)
    - [`internal_camera_node.py` speciality](#internal_camera_nodepy-speciality)
    - [`viewer_node.py` — Viewer (used for testing purposes)](#viewer_nodepy--viewer-used-for-testing-purposes)
  - [Launch File](#launch-file)
    - [`auto_camera_launch.py`](#auto_camera_launchpy)
    - [`gui_camera_launch.py`](#gui_camera_launchpy)
  - [Running the package](#running-the-package)
  - [TESTING](#testing)

---

## Package Structure

``` graph
cameras/
├── launch/
|   ├── auto_camera_launch.py # Launch file for camera feed in auto mode
|   └── gui_camera_launch.py # Launch file for camera feed in GUI mode  
└── cameras/
    ├── external_camera_node.py # camera publisher for feed through router
    ├── internal_camera_node.py # camera publisher for internal use of feed
    └── viewer_node.py # Dual-camera viewer node (testing purposes)
```

---

## Nodes

### for both `external_camera_node.py` and `internal_camera_node.py`

opens a camera via OpenCV and publishes frames as ROS 2 type message

#### Parameters

| Parameter      | Type   | Default               | Description                         |
| -------------- | ------ | --------------------- | ----------------------------------- |
| `device_index` | int    | `0`                   | Camera device index (`/dev/videoN`) |
| `publish_rate` | float  | `15.0`                | Publishing rate in Hz               |
| `frame_id`     | string | `"camera"`            | TF frame ID stamped on each message |
| `topic`        | string | `"/camera/image_raw"` | Topic to publish images on          |

#### QoS Profile

```python
qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
```

optimised for efficient data transmission, especially over WiFi.
> ⚠️ WARNING: make sure that the subscriber uses a compatible QoS profile

### `external_camera_node.py` speciality

uses the `sensor_msgs.msg.CompressedImage` type and compresses the image to only **40%** of the original size before publishing. This is useful for sending camera feed over a network reliably.

> used for external processing of camera feed; aka GUI run

### `internal_camera_node.py` speciality

uses the  `sensor_msgs/Image` messages for easy processing in other ROS 2 nodes.

> used for internal processing of camera feed; aka autonomous run

### `viewer_node.py` — Viewer (used for testing purposes)

Subscribes to two camera topics and displays each feed in its own OpenCV window.

**Subscribed Topics**

| Topic                | Type                | QoS                                        |
| -------------------- | ------------------- | ------------------------------------------ |
| `/camera1/image_raw` | `sensor_msgs/Image` | Best Effort, Volatile, Keep Last (depth 1) |
| `/camera2/image_raw` | `sensor_msgs/Image` | Best Effort, Volatile, Keep Last (depth 1) |

---

## Launch File

### `auto_camera_launch.py`

starts the `internal_camera_node` with the following configuration:

``` python
parameters=[{
                'device_index': 4,
                'publish_rate': 15.0,
                'topic': '/camera/image_raw',
                'frame_id': 'camera',
            }],
```

### `gui_camera_launch.py`

starts the `external_camera_node` with the following configuration:

``` python
parameters=[{
                'device_index': 4,
                'publish_rate': 15.0,
                'topic': '/camera1/image_raw',
                'frame_id': 'camera1',
            }],
```

---

## Running the package

Launch launch file according to the mode you want to run the camera feed in

## TESTING

both launchs/nodes where testing separately and works as intended.

> ‼️CARE‼️: </br>
> the launch file did not handle the case when the modes are switched </br>
> in the competition we did not switch the modes </br>
> to switch modes with correct handling camera feed publishing the logic must be revised and re-tested!!
