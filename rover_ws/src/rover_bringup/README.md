# Rover Bringup Package
package only conatins launch files to start the rover with all the required nodes and parameters.

## Launch Files

### `auto_launch.py`
launches the rover in autonomous mode with the lane_follower approach - lane following only **no obstacle or pothole avoidance**. It was intended to have the final fully working approach but we did not reach this level of development. 

>**UNTESTED**

### `manual_launch.py`
launches the rover in manual mode with the necessary nodes and parameters for manual control using **controller**.

>**TESTED** and **USED**

### `teleop_launch.py`
launches the rover in teleoperation mode with the necessary nodes and parameters for remote control using **keyboard**.

>**TESTED** and **USED**
