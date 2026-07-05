import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import ExecuteProcess, TimerAction

def generate_launch_description():

    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[os.path.join(
            get_package_share_directory('rover_localization'),
            'config', 'ekf.yaml'
        )]
    )

    imu_republisher_node = Node(
        package='rover_localization',
        executable='imu_republisher',   # ✅ drop the .py extension
        name='imu_republisher_node',
        output='screen'
    )

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[os.path.join(
            get_package_share_directory('rover_localization'),
            'config', 'online_async.yaml'
        )]
    )

    activate_slam_configure = TimerAction(
        period=3.0,
        actions=[ExecuteProcess(
            cmd=['ros2', 'lifecycle', 'set', '/slam_toolbox', 'configure'],
            output='screen'
        )]
    )

    activate_slam_activate = TimerAction(
        period=5.0,
        actions=[ExecuteProcess(
            cmd=['ros2', 'lifecycle', 'set', '/slam_toolbox', 'activate'],
            output='screen'
        )]
    )
    return LaunchDescription([
        robot_localization_node,
        imu_republisher_node,
        slam_toolbox_node,
        activate_slam_configure,
        activate_slam_activate
    ])