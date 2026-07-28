# Mission Package
this package contains the mission node that controls the rover's behavior based on the current state of the mission - **State Machine Node**. It subscribes to various topics to receive sensor data and publishes commands to control the rover's actuators.

- [Mission Package](#mission-package)
  - [Package Structure](#package-structure)
  - [Nodes](#nodes)
    - [`mission_node.py`](#mission_nodepy)
      - [Parameters - from `params.yaml`](#parameters---from-paramsyaml)
      - [Topics](#topics)
    - [`test_node.py`](#test_nodepy)
    - [`auto_led.py`](#auto_ledpy)
  - [Launch Files](#launch-files)
    - [`mission_auto.launch.py`](#mission_autolaunchpy)
    - [`mission_manual.launch.py`](#mission_manuallaunchpy)
  - [Runnning the pkg](#runnning-the-pkg)
  - [Testing](#testing)
  

---

## Package Structure

``` graph
mission/
├── config/
|   └── params.yaml # Configuration file for mission_node.py      
├── launch/
|   ├── mission_auto.launch.py # Launch file for the mission node in auto mode
|   └── mission_manual.launch.py # Launch file for the mission node in manual mode
├── mission/
|   ├── mission_node.py # Main mission node implementing the state machine
|   ├── auto_led.py # Node to control the LED in auto mode
|   └── test_node.py # Node for testing mission node
└── tests/
    # Unit tests for mission_node.py, with complete honesty -> AI generated wa m4 faker 2wy, bs implementation worked - can be refrence for future work regarding learninig about unit tests 
```

---

## Nodes

### `mission_node.py`
This node implements the state machine that controls the rover's behavior based on the current state of the rover </br>

**States**:
- `MANUAL` : Manual control mode
- `AUTO_LANES` : Autonomous lane following mode
- `AUTO_WAYPOINTS` : Autonomous waypoining mode
- `AUTO_WAYPOINT2` : Autonomous waypoint 2 mode - Face recognition mode

> ⚠️ Warning </br>
> the mission node was missing small things - any mission part is commented with a pseudocode placeholder.

#### Parameters - from `params.yaml`
- mode: 0 for absolute manual (no switching to manual); 1 for switching between manual and auto
- 3 gps values - latitude and longitude - for waypoints 1,2 and 3

#### Topics

```python
LOCALIZATION_TOPIC = '/odom/global' # subscribe
GPS_TOPIC = '/gps/fix' # subscribe
FACE_RECOGNITION_SERVICE = '/face_recognition/start' # service call to start and end face recognition
WAYPOINT_NAVIGATION_SERVICE = 'generate_bezier_path' # action call to generate waypoint path
MANUAL_TOGGLE_TOPIC = '/manual_toggle' # subscribe to change between manual and auto if mode is set to 1
STATE_TOPIC = '/mission/active_state' # publish to be used by other nodes especially the cmd_vel mux node
```

### `test_node.py`

small simulator for testing the state tranisions in `mission_node.py` 

### `auto_led.py`

subscribes to the `/manual_toggle` and controls the LED based on the current state of the mission by publishing to the topic for controlling led output. 
> current topic written is `/rover/mode` m4 3aref kan final wala l2 </br>
> only tested software side, **not tested on hardware** </br>

---

## Launch Files

### `mission_auto.launch.py`

launch the mission node in auto mode with the parms.yaml configuration file

> not tested

### `mission_manual.launch.py`

launch the mission node in manual mode with parsed `mode=0` (no need for waypoint coordinates since it is manual only)

> it was practically used on site, this launch file was called in the bringup launch file for manual run

--

## Runnning the pkg

it is clear, using launch files only, no need to run nodes separately.

---

##  Testing 

mentioned for each part, generally only manual was testied practically
others softwrae tested not real world testing

