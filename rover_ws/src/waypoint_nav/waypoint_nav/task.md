# waypoint_nav

This package is responsible for autonomous path planning, trajectory smoothing, and tracking using GPS waypoints. The system consists of two main nodes that seamlessly integrate and communicate via **ROS 2**.

---

## 1. Trajectory Node (`trajectory.py`)

### Overview
This node acts as the **Global Path Planner**. It reads geographic coordinates (GPS Waypoints) from an external YAML configuration file, converts them into a local Cartesian coordinate system ($X, Y$) in meters relative to the robot's initial position, and then generates a smooth, continuous global trajectory connecting these points using **Cubic Bezier Curves**.

### Subscribers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/odom` | `nav_msgs/msg/Odometry` | Captures the robot's initial starting position to anchor the local coordinate system ($X=0, Y=0$). | `SENSOR_DATA` |

### Publishers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/controller/path` | `nav_msgs/msg/Path` | The complete generated path consisting of sequential dense points for the controller to track. | `TRANSIENT_LOCAL` (Latched) |
| `/controller/waypoints` | `visualization_msgs/msg/MarkerArray` | 3D markers (green spheres + text labels) to visualize the original input waypoints in RViz. | `TRANSIENT_LOCAL` (Latched) |

### Parameters
* `waypoints_file` *(string)*: Relative or absolute path to the YAML file containing the GPS waypoints.
* `control_scale` *(float)*: The ratio of the Bezier control arm length relative to the segment length (controls turning smoothness).
* `min_control_dist` *(float)*: The minimum allowable control arm length in meters to prevent sharp transitions.
* `points_per_meter` *(int)*: Density of the generated points per meter along the path.
* `republish_rate_sec` *(float)*: The periodic interval to re-publish the static path so late-starting nodes or RViz can capture it.

---

## 2. Controller Node (`controller.py`)

### Overview
This node acts as the **Local Path Follower** utilizing a geometric **Pure Pursuit** steering algorithm backed by a Finite State Machine (FSM). By subscribing to the generated path and the robot's real-time position via Odometry, it calculates the angular velocity ($\omega$) required to target a dynamic look-ahead point, while handling sequential states from orientation alignment to target arrival.

### Subscribers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/controller/path` | `nav_msgs/msg/Path` | The target path received from the path planner. | `TRANSIENT_LOCAL` (Latched) |
| `/odom` | `nav_msgs/msg/Odometry` | Continually updates the robot's exact estimated 2D pose $(x, y, \theta)$ via odometry. | `SENSOR_DATA` |

### Publishers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | Velocity commands containing stamped linear velocity ($v$) and angular velocity ($\omega$). | `RELIABLE` (Depth: 10) |
| `/controller/lookahead` | `geometry_msgs/msg/PointStamped` | Coordinates of the active look-ahead point being targeted, useful for RViz debugging. | `RELIABLE` (Depth: 10) |
| `/controller/fsm_state` | `std_msgs/msg/String` | The current operational state of the controller's Finite State Machine. | `RELIABLE` (Depth: 10) |

### Finite State Machine (FSM States)
1. **`WAITING_FOR_PATH`**: The robot remains stationary, publishing zero velocity, waiting to receive its first valid reference trajectory.
2. **`GO_TO_START`**: Executed if the robot is away from the path origin. The robot spins in place using a Proportional P-Controller to align its heading with the first path segment to avoid aggressive initial overshoots.
3. **`NAVIGATING`**: The robot actively tracks the path, executing Pure Pursuit geometry. It automatically skips the first 5 dense/stacked points to prevent tracking lag, smoothly following the S-Curve.
4. **`GOAL_REACHED`**: The robot safely arrives within the threshold of the final waypoint, triggering a complete stop sequence.

### Parameters
* `lookahead_distance` *(float)*: The look-ahead distance ($L$) in meters. Higher values ($0.5\text{m} - 0.6\text{m}$) stabilize driving through dynamic planning S-curves, while lower values track tightly but can cause steering oscillations (fishtailing).
* `desired_velocity` *(float)*: The constant target linear velocity ($m/s$) during navigation.
* `goal_threshold` *(float)*: Acceptance radius around the final goal point to declare a successful arrival.

---

## Data Flow Summary

1. The **Trajectory Node** parses the YAML configuration $\rightarrow$ transforms GPS to Local XY meters anchored to initial Odom $\rightarrow$ publishes the global path onto `/controller/path`.
2. The **Controller Node** intercepts the path $\rightarrow$ checks real-time robot localization via `/odom` $\rightarrow$ handles the FSM logic and guards tracking against continuous re-planning loops.
3. The **Controller Node** isolates the dynamic look-ahead point, computes the required steering adjustments, and streams clean stamped $v$ and $\omega$ values to the `/cmd_vel` topic to pilot the hardware drivetrain.