# rover_ws code documentation

src </br>
├── [cameras](src/cameras/README.md) </br>
├── [face_recognition](src/face_recognition/README.md) </br>
├── [imu_tools](src/imu_tools/README.md) </br>
├── [lane_detector_pkg](src/lane_detector_pkg/README.md) </br>
├── [lazer_servo](src/lazer_servo/README.md) </br>
├── [localization](src/localization/README.md) </br>
├── [mission](src/mission/README.md) </br>
├── [motion](src/motion/README.md) </br>
├── [obstacle_avoidance](src/obstacle_avoidance/README.md) </br>
├── [phyphox](src/phyphox/README.md) </br>
├── [pid_navigation](src/pid_navigation/README.md) </br>
├── [road_detector](src/road_detector/README.md) </br>
├── [rover_bringup](src/rover_bringup/README.md) </br>
├── [rover_embedded](src/rover_embedded/README.md) </br>
├── [rover_interfaces](src/rover_interfaces/README.md) </br>
├── [waypoint_nav](src/waypoint_nav/README.md) </br>

## autonomous code approaches

### approach 1

find offset to center of where you want the rover to go (widest gap), and use PID to correct the rover's heading to go towards that point.

#### approach 1.1

using classical/models to detect then calculate the offset in meters using 1 camera and homography to get the distance to the point of interest. </br>
PID usies meters offset to correct heading.

#### approach 1.2

using classical/models to detect then calculate the angle using the camera's field of view and the pixel offset to the point of interest. </br>
PID uses angle offset to correct heading. (**pid was not impolemented** in this approach)

### approach 2 - pointclouds based approach

#### approach 2.1

using nav2 library taking inputs: pointclouds from lidar (obstacles) and road_detector (lanes and pot holes) </br>
(**failed good implemnetation**, trys are on the branch: `ros/nav2`)

#### approach 2.2

using lanes detected via road_detector to plan lanes and follow them </br>
integrating pot holes and lidar obstacles while lane following was **not implemented**
