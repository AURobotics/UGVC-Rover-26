ros pkgs is to be added in the src folder here

## Useful Commands

### Windows Notes
> - You must used CMD not powershell
> - steps to run code: build, source, run

### Create a new package

> - make sure you are inside the src folder 
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

### Source pkg

ubuntu
```bash
source install/setup.bash
```

windows
```cmd
call install\setup.bat
```

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

