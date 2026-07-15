from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    
    stm32_node = Node(
        package='rover_embedded',       
        executable='stm_node',
        name='stm_node',
        output='screen',
        emulate_tty=True,

    )
    twist_node = Node(
        package='motion',       
        executable='twist_node',
        name='twist_node',
        output='screen',

    )

    linear_speed = Node(
        package='rover_embedded',
        executable='linear_vel',
        name='linear_vel_node',
        output='screen',
    )

    return LaunchDescription([
        stm32_node,
        linear_speed,
        # twist_node
    ])