"""
mission_launch.py
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
    GroupAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition, UnlessCondition


def generate_launch_description():
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")
    mission_nav2_dir = get_package_share_directory("mission_nav2")

    # use_gps:=false (default) -> sim / no-GPS: odom-only, nav2_params2.yaml
    # use_gps:=true            -> hardware: GPS global localization, nav2_params_gps.yaml
    declare_use_gps = DeclareLaunchArgument(
        "use_gps", default_value="true",
        description="True on hardware with GPS: brings up navsat_transform + global EKF "
                    "and switches Nav2 to use the map frame.",
    )
    use_gps = LaunchConfiguration("use_gps")

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=PythonExpression([
            "'", os.path.join(mission_nav2_dir, "config", "nav2_params_gps.yaml"),
            "' if '", use_gps, "' == 'true' else '",
            os.path.join(mission_nav2_dir, "config", "nav2_params2.yaml"), "'"
        ]),
        description="Full path to the Nav2 params file to use "
                    "(auto-selected from use_gps unless overridden explicitly)",
    )
    
    # Keep the default as false so it defaults to real hardware, 
    # but we can easily toggle it from the CLI for simulation.
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false",
        description="Use simulation clock if true",
    )

    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Launch RViz2')
    use_rviz     = LaunchConfiguration('use_rviz')

    # ------------------------------------------------------------------ #
    #  RViz                                                              #
    # ------------------------------------------------------------------ #
    rover_nav_dir = get_package_share_directory('rover_navigation')
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

    # ---- 1. Localization: sim/no-GPS uses local_launch.py only,       -----
    # ----    hardware uses global_launch.py (local EKF + navsat +      -----
    # ----    global EKF, includes local_launch.py itself -- don't      -----
    # ----    include local_launch.py separately or you'll double it up)-----
    localization_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("localization"), "launch", "local_launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
        condition=UnlessCondition(use_gps),
    )
    localization_gps = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("localization"), "launch", "global_launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
        condition=IfCondition(use_gps),
    )

    # ---- 2. Nav2 Navigation Stack -------------------------------------------
    # NOTE: using OUR trimmed copy of navigation_launch.py (in this package's
    # launch/ folder), not nav2_bringup's stock one -- the stock file
    # hardcodes collision_monitor + docking_server into lifecycle_nodes with
    # no way to disable them via params/CLI, so we removed them at the source.
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("mission_nav2"),
                "launch", "navigation_launch.py")
        ),
        launch_arguments={
            "params_file": params_file,
            "use_sim_time": use_sim_time,
            "autostart": "true",
        }.items(),
    )

    # ---- 3. Mission Manager -------------------------------------------------
    mission_manager = Node(
        package="mission_nav2",
        executable="waypoint_navigation",
        name="mission_manager",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )
    delayed_mission_manager = TimerAction(period=10.0, actions=[mission_manager])

    # ---- 4. Road Detector Node ----------------------------------------------
    road_detector_node = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        # FIXED: Changed from hardcoded {'use_sim_time': True} to use the variable tracking use_sim_time
        parameters=[
            os.path.join(get_package_share_directory('road_detector'), 'config', 'params_sim.yaml'),
            {'use_sim_time': use_sim_time} 
        ],
        additional_env={'PYTHONUNBUFFERED': '1'},
        output='screen'
    )

    return LaunchDescription([
        params_file_arg,
        use_sim_time_arg,
        declare_use_gps,
        declare_use_rviz,
        rviz,
        road_detector_node,
        localization_sim,
        localization_gps,
        navigation,
        delayed_mission_manager,
    ])

    # for sim:
    # ros2 launch mission_nav2 mission.launch.py use_sim_time:=true use_gps:=false