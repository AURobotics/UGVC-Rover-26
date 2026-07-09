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

    return LaunchDescription([
        stm32_node,
        
    ])