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
ros2 run lane_detector_pkg testOfLanes
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





#target_center = filtered_center ## new target center (bec holes)
        #hole_found = False
        #for box in results_hole.boxes:
        #    conf = float(box.conf[0])
         #   if conf < 0.5:
        #        continue
          #  z1,k1,z2,k2 = map(int,box.xyxy[0])
          #  hole_center_x = (z1 + z2) / 2  
           # if x_left is not None and x_right is not None :
         #       left_boundary = x_left
      #          right_boundary = x_right
      #      elif x_left is not None and x_right is None : 
      #          left_boundary = x_left
      #          right_boundary = x_left + self.prev_lane_width
       #     elif x_right is not None and x_left is None :
        #        right_boundary = x_right
        #        left_boundary = x_right - self.prev_lane_width
        #    else :
        #        left_boundary = self.last_known_center - self.prev_lane_width // 2
         #       right_boundary = self.last_known_center + self.prev_lane_width // 2

         #   if x1 <= left_boundary or x2 >= right_boundary:
          #      continue  

          #  cv2.rectangle(frame, (z1, k1), (z2, k2), (0, 255, 255), 2) # to show boxes

         #   left_distance = z1 - left_boundary
         #   right_distance = right_boundary - z2

          #  margine = 10 

          #  if left_distance >= right_distance:
          #      target_center = (z1 + left_boundary) // 2 - margine
          #  elif right_distance > left_distance:
          #      target_center = (z2 + right_boundary) // 2 + margine

          #  hole_found = True
          #  break  
        #print(hole_found)
        #if hole_found:
        #    final_error = target_center - X_target
        #else:
           # final_error = lane_error_pixels