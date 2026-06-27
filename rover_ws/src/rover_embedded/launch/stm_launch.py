from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='Serial port for the STM32 (e.g. /dev/ttyACM0)',
    )
    linear_speed_arg = DeclareLaunchArgument(
        'linear_speed',
        default_value='0.5',
        description='Max linear speed sent by the teleop node (m/s)',
    )
    angular_speed_arg = DeclareLaunchArgument(
        'angular_speed',
        default_value='1.0',
        description='Max angular speed sent by the teleop node (rad/s)',
    )

   
    stm32_node = Node(
        package='rover_embedded',       
        executable='stm_node',
        name='stm_node',
        output='screen',
        emulate_tty=True,
        parameters=[
            {'port': LaunchConfiguration('port')},
        ],
    )

    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        emulate_tty=True,         
        prefix='xterm -e',          
        remappings=[
            ('/cmd_vel', '/cmd_speed'),  # remap cmd_vel to cmd_speed for STM32Node
        ],
        parameters=[{
            'speed':       LaunchConfiguration('linear_speed'),
            'turn':        LaunchConfiguration('angular_speed'),
            'repeat_rate': 10.0,    
            'key_timeout':  0.6,    
        }],
    )

    return LaunchDescription([
        port_arg,
        linear_speed_arg,
        angular_speed_arg,
        stm32_node,
        teleop_node,
    ])