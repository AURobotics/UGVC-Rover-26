# Rover WS

This folder covers the Rover sub-project, which is responsible for the high level control code that lives inside the on-board computer.

## Tech Stack

- ROS2 (Jazzy)
    - Using the RoboStack Conda distribution channel [↗️](https://robostack.github.io/GettingStarted.html)
- Pixi, for cross-platform ROS2 and Python package management [↗️](https://pixi.prefix.dev/latest/robotics/)

## Contributing

### Project Setup

After cloning the mono-repo, open the `rover_ws/` folder inside your favorite text editor or IDE.

### Pre-requisites

#### Installing Pixi [↗️](https://pixi.prefix.dev/latest/installation/)

Windows
```pwsh
winget install prefix-dev.pixi
```

Linux/ MacOS
```sh
curl -fsSL https://pixi.sh/install.sh | bash
```

#### Installing project dependencies

Make sure you are in a pixi-activated shell
```sh
pixi shell
```

Then, run:
```sh
pixi install
```


## to try the simple publisher 
cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 run lane_detector_pkg ObstacleAndLanes

cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 run lane_detector_pkg testOfLanes

cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 launch lane_detector_pkg test.launch.py

 
# in new terminal
cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 topic echo /lane/error

cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 topic echo /lane/left_x

cd ~/UGVC-Rover-26/rover_ws
rm -rf build install log
colcon build --packages-select lane_detector_pkg
source install/setup.bash
ros2 topic echo /lane/right_x

