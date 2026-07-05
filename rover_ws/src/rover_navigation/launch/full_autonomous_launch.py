#!/usr/bin/env python3

import os
import yaml
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    rover_nav_dir = get_package_share_directory('rover_navigation')
    # rover_precp_dir = get_package_share_directory('rover_perception')
    # ------------------------------------------------------------------ #
    #  BT XML paths                                                        #
    # ------------------------------------------------------------------ #
    bt_pose_xml  = os.path.join(
        rover_nav_dir, 'behavior_trees', 'navigate_to_pose.xml')
    bt_poses_xml = os.path.join(
        rover_nav_dir, 'behavior_trees', 'navigate_through_poses.xml')

    for f in (bt_pose_xml, bt_poses_xml):
        if not os.path.isfile(f):
            raise RuntimeError(
                f'BT XML missing — did you colcon build?\n  {f}'
            )

    # ------------------------------------------------------------------ #
    #  Patch nav2_params.yaml — inject BT XML paths                       #
    # ------------------------------------------------------------------ #
    src_params = os.path.join(rover_nav_dir, 'config', 'nav2_params.yaml')
    # road_detector_params = os.path.join(rover_precp_dir, 'config', 'road_detector_params.yaml')
    # lane_follower_params = os.path.join(rover_precp_dir, 'config', 'lane_follower_params.yaml')
    with open(src_params, 'r') as fh:
        params = yaml.safe_load(fh)

    params['bt_navigator']['ros__parameters']['default_nav_to_pose_bt_xml']      = bt_pose_xml
    params['bt_navigator']['ros__parameters']['default_nav_through_poses_bt_xml'] = bt_poses_xml

    patched = tempfile.NamedTemporaryFile(
        mode='w', prefix='nav2_params_patched_', suffix='.yaml', delete=False)
    yaml.dump(params, patched)
    patched.close()
    patched_params = patched.name

    # ------------------------------------------------------------------ #
    #  Launch arguments                                                    #
    # ------------------------------------------------------------------ #
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use /clock (Gazebo) or wall clock')

    declare_slam_params = DeclareLaunchArgument(
        'slam_params_file',
        default_value=os.path.join(
            get_package_share_directory('rover_localization'), 'config', 'online_async.yaml'),
        description='Path to SLAM Toolbox parameter file')

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Launch RViz2')

    declare_log_level = DeclareLaunchArgument(
        'log_level', default_value='info')

    declare_lookahead = DeclareLaunchArgument(
        'lookahead_distance', default_value='2.5',
        description='Metres ahead of robot to place each lane-following goal')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz     = LaunchConfiguration('use_rviz')
    log_level    = LaunchConfiguration('log_level')

    # ------------------------------------------------------------------ #
    #  RViz — reuse rviz.launch.py, point at nav2 config                  #
    # ------------------------------------------------------------------ #
    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rover_nav_dir, 'launch', 'rvizz.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'rviz_config':  os.path.join(rover_nav_dir, 'rviz', 'rover_teleop.rviz'),
        }.items(),
        condition=IfCondition(use_rviz),
    )

    # ------------------------------------------------------------------ #
    #  Localization (EKF + IMU republisher)                               #
    # ------------------------------------------------------------------ #
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('rover_localization'),
            'launch', 'local_localization.launch.py',
        )])
    )


    # ------------------------------------------------------------------ #
    #  Nav2 stack                                                          #
    # ------------------------------------------------------------------ #
    nav2_launch = TimerAction(
    period=5.0,   # wait 10s for SLAM to init and publish map frame
    actions=[
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(rover_nav_dir, 'launch', 'nav2.launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file':  patched_params,
                'autostart':    'true',
                'slam': 'false',
            }.items(),
        )
    ]
)

    # ------------------------------------------------------------------ #
    #  Virtual Wall Node (t +3 s)                                         #
    # ------------------------------------------------------------------ #
    # virtual_wall_node = TimerAction(
    #     period=3.0,
    #     actions=[
    #         Node(
    #             package='rover_perception',
    #             executable='road_detector_node',
    #             name='road_detector_node',
    #             output='screen',
    #             parameters=[road_detector_params, {'use_sim_time': use_sim_time}],
    #             arguments=['--ros-args', '--log-level', log_level],
    #             remappings=[
    #                 ('/camera/image_raw',       '/camera/image_raw'),
    #                 ('/camera/depth/image_raw', '/camera/depth/image_raw'),
    #                 ('/virtual_walls',          '/virtual_walls'),
    #             ],
    #         )
    #     ],
    # )

    # ------------------------------------------------------------------ #
    #  Lane Follower Node (t +10 s)                                       #
    # ------------------------------------------------------------------ #
    # lane_follower = TimerAction(
    #     period=10.0,
    #     actions=[
    #         Node(
    #             package='rover_perception',
    #             executable='lane_follower_node',
    #             name='lane_follower_node',
    #             output='screen',
    #             parameters=[lane_follower_params, {
    #                 'use_sim_time':       use_sim_time,
    #                 'min_remaining_dist': 0.8,
    #                 'startup_delay_sec':  0.0,
    #                 'nav_goal_timeout':   25.0,
    #             }],
    #             arguments=['--ros-args', '--log-level', log_level],
    #         )
    #     ],
    # )

    # ------------------------------------------------------------------ #
    #  twist_stamper                                                       #
    # ------------------------------------------------------------------ #
    twist_stamper = Node(
        package='rover_controller',
        executable='twist_stamper',
        name='twist_stamper',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ------------------------------------------------------------------ #
    #  Startup banner                                                      #
    # ------------------------------------------------------------------ #
    startup_msg = LogInfo(
        msg=[
            '\n',
            '╔══════════════════════════════════════════════════╗\n',
            '║   rover — Lane-Aware Autonomous Navigation        ║\n',
            '║   SLAM Toolbox + Nav2 + Virtual Walls             ║\n',
            '║   Lane follower: continuous forward goals         ║\n',
            '╚══════════════════════════════════════════════════╝\n',
            f'BT XML (pose)  = {bt_pose_xml}\n',
            f'BT XML (poses) = {bt_poses_xml}\n',
            f'Patched params = {patched_params}\n',
            'use_sim_time   = ', use_sim_time, '\n',
            'use_rviz       = ', use_rviz, '\n',
            'Lane follower starts at t +10 s (SLAM warm-up delay)\n',
            'Press Ctrl-C to stop the robot.\n',
        ]
    )

    road_detector = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        parameters=[os.path.join(get_package_share_directory('road_detector'), 'config', 'params_sim.yaml'),
                    {'use_sim_time': True}],
        additional_env={'PYTHONUNBUFFERED': '1'}, # <-- Forces logs to flush instantly
        output='screen'
    )

    noisy_controller = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('rover_controller'),
            'launch', 'controller.launch.py',
        )])
    )

    return LaunchDescription([
        declare_use_sim_time,
        # declare_slam_params,
        declare_use_rviz,
        declare_log_level,
        declare_lookahead,
        startup_msg,
        noisy_controller,
        # localization,
        nav2_launch,
        # virtual_wall_node,
        # lane_follower,
        rviz,            # ← now uses shared rviz.launch.py
        twist_stamper,
        road_detector,  
    ])