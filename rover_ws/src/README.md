## Table of contents

- [Table of contents](#table-of-contents)
- [Running pkgs with cmake](#running-pkgs-with-cmake)
  - [Cmake file changes:](#cmake-file-changes)
  - [For windows users](#for-windows-users)
- [Useful Commands](#useful-commands)
  - [Windows Notes](#windows-notes)
  - [Create a new package](#create-a-new-package)
  - [Build pkg](#build-pkg)
  - [Source](#source)
  - [Run a Node](#run-a-node)
  - [Run a launch file](#run-a-launch-file)
  - [Usful Topic commands](#usful-topic-commands)
  - [Run RViz2](#run-rviz2)
  - [Run Gazebo](#run-gazebo)

---

## Building packages with cmake

### Cmake file changes:
- add this to the begining of the cmake file:
```Cmake
cmake_minimum_required(VERSION 3.12...3.40)
```

- Dependencies should be grouped as the following example:
```Cmake
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Speed.msg"
  "msg/WheelVel.msg"
  "msg/RoverStatus.msg"
  "srv/MyService.srv"
  # ... other custome interfaces you made
  DEPENDENCIES 
    std_msgs
    geometry_msgs
    # ... other dependencies 
)
```

### Prerequisites (Windows)
Install the 2022 MSVC build tools:
```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --source winget --force --accept-package-agreements --accept-source-agreements --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --wait /norestart"
```

RoboStack uses [vinca](https://github.com/RoboStack/vinca/) to generate workflows for building their ROS2 binaries. As of writing this, vinca's [GitHub action generator](https://github.com/RoboStack/vinca/blob/master/vinca/generate_gha.py) uses Visual Studio 2022 runners. This may change in the future, and the proper `winget` command may require a simple Visual Studio version change.

## Useful Commands

### Windows Notes
> - your path to the repo must have **no spaces**
> - steps to run code: build, run; no longer needs to source (automated by pixi.toml)

### Create a new package

> - make sure you are **inside the src folder** 
> - change my_package with your pkg name

C++ pkg
```bash
ros2 pkg create my_package --build-type ament_cmake --dependencies rclcpp std_msgs
```

Python pkg
```bash
ros2 pkg create my_package --build-type ament_python --dependencies rclpy
```

### Build pkg

build all pkgs
```bash
colcon build
```

build specific pkgs
```bash
colcon build --packages-select package1 package2 package3
```

> **for windows write `pixi run` before colcon even if you are in the shell**

### Source

ubuntu
```bash
source install/setup.bash
```

windows
```cmd
call install\setup.bat
```
> windows no longer needs to source, automatically done by pixi

### Run a Node

> - change pkg_name with your pkg name
> - change node_name with name written in setup.py refering to this node

```bash
ros2 run pkg_name node_name
```

### Run a launch file

> - change pkg_name with your pkg name
> - change launch_file.py with its name and DONT forget the .py
> - Note: a line needs to be added in setup.py for the launch file to work

no args needed:
```bash
ros2 launch pkg_name launch_file.py
```

with args:
```bash
ros2 launch pkg_name launch_file.py arg_name1:=arg_data1 arg_name2:=arg_data2
```

### Usful Topic commands

| Command                                  | Function                                                         | Example |
| :--------------------------------------- | :--------------------------------------------------------------- | :------ |
| **`ros2 topic list`**                    | List all active topics.                                          |
| **`ros2 topic list -t`**                 | List all active topics with their data types                     |
| **`ros2 topic echo /topic/name`**        | Print messages from a /topic/name to the console.                |
| **`ros2 topic echo /topic/name --once`** | Print one meesage from /topic/name to the console.               |
| **`ros2 topic info /topic/name`**        | Show publisher & subscriber count and topic type of /topic/name. |
| **`ros2 topic hz /topic/name`**          | Report the average publishing rate of /topic/name.               |

<<<<<<< HEAD
### Run RViz2
```bash
pixi run rviz
```

or use a launch file that includes rviz2


### Run Gazebo

run a a launch file that includes gazebo, for example:

> [!WARNING]
> Gazebo only works on Linux


=======
>>>>>>> ros-motion
