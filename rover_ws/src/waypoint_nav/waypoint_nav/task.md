# waypoint_nav

This package is responsible for autonomous path planning, trajectory smoothing, and tracking using GPS waypoints. The package implements a highly modular **Action-Based Client-Server Architecture** integrated via **ROS 2**, splitting the high-level task management from the low-level calculation and execution loops.

---

## 1. Waypoint Action Client Node (`controller.py`)

### Overview
This node serves as the **Orchestrator / High-Level Decision Maker** (representing the core of the system's FSM). It handles data entry and mission monitoring. It reads geographic coordinates (GPS Waypoints) from an external YAML configuration file, packages them into a ROS 2 Action Goal, and commands the server to execute the path. It operates asynchronously, continually logging feedback from the server until successful mission completion.

### Action Clients
| Action Name | Action Type | Description |
| :--- | :--- | :--- |
| `generate_bezier_path` | `rover_interfaces::action::GenerateBezierPath` | Sends the raw GPS trajectory to the server, monitors live tracking feedback, and receives the final mission success result. |

### Parameters
* `waypoints_file` *(string)*: Relative or absolute path to the YAML file containing the target GPS waypoints. Defaults to `config/waypoints.yaml`.

---

## 2. Bezier Path Action Server Node (`trajectory.py`)

### Overview
This node acts as the **Hybrid Execution Unit**, combining the roles of **Global Path Planner**, **Local Path Follower (Controller)**, and **Safety Handler**. Upon receiving an action goal, it transforms the GPS coordinates into a local Cartesian coordinate system ($X, Y$) in meters. It then generates a continuous trajectory using **Cubic Bezier Curves** and runs a high-frequency **Pure Pursuit** control loop to drive the rover drivetrain.

### Action Servers
| Action Name | Action Type | Description |
| :--- | :--- | :--- |
| `generate_bezier_path` | `rover_interfaces::action::GenerateBezierPath` | Executes the path generation, manages the tracking loop, and streams real-time feedback (robot coordinates) back to the client. |

### Subscribers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/odom` | `nav_msgs/msg/Odometry` | Continually updates the robot's exact estimated 2D pose $(x, y, \theta)$ required for the Pure Pursuit controller. | `RELIABLE` (Depth: 10) |
| `/fsm/emergency_stop` | `std_msgs/msg/Bool` | Listens for explicit emergency commands from high-level FSMs or obstacle avoidance nodes to immediately freeze the vehicle. | `RELIABLE` (Depth: 10) |

### Publishers
| Topic Name | Message Type | Description | QoS Policy |
| :--- | :--- | :--- | :--- |
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | Stamped velocity commands containing the computed linear velocity ($v$) and angular steering velocity ($\omega$) for the simulator/drivetrain. | `RELIABLE` (Depth: 10) |
| `/controller/dense_path` | `nav_msgs/msg/Path` | The complete generated smooth path consisting of sequential dense points, published for RViz visualization. | `TRANSIENT_LOCAL` (Latched) |
| `/controller/waypoint_markers` | `visualization_msgs/msg/MarkerArray` | 3D Marker spheres (bright blue) to visualize the original input waypoints in RViz. | `TRANSIENT_LOCAL` (Latched) |

### Trajectory & Control Parameters
* `control_scale` *(float)*: The ratio of the Bezier control arm length relative to the segment length (controls turning smoothness).
* `min_control_dist` *(float)*: The minimum allowable control arm length in meters to prevent sharp transitions.
* `points_per_meter` *(int)*: Density of the generated dense points per meter along the path.
* `lookahead_dist` *(float)*: The look-ahead distance ($L_d$) in meters used by the Pure Pursuit geometry to calculate steering adjustments.
* `linear_velocity` *(float)*: The constant target linear velocity ($m/s$) during navigation.

---

## Safety Features (Emergency Stop)
The **Bezier Path Action Server** includes an integrated safety guard loop. If a `True` message is detected on the `/fsm/emergency_stop` topic at any time during execution:
1. The internal control loop is immediately deactivated.
2. A stamped zero-velocity message is published to `/cmd_vel` to freeze the rover drivetrain.
3. The active action goal is instantly aborted, notifying the client of an forced safety shutdown.

