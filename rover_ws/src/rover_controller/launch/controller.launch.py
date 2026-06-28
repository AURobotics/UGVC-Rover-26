from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration

def launch_noisy_controller(context, *args, **kwargs):
    # Retrieve values and compute the noisy parameters dynamically
    wheel_radius = float(LaunchConfiguration("wheel_radius").perform(context))
    wheel_separation = float(LaunchConfiguration("wheel_separation").perform(context))
    wheel_radius_error = float(LaunchConfiguration("wheel_radius_error").perform(context))
    wheel_separation_error = float(LaunchConfiguration("wheel_separation_error").perform(context))

    # Create the noisy_controller node with perturbed parameters
    noisy_controller_node = Node(
        package="rover_controller", 
        executable="noisy_controller",
        parameters=[
            {"wheel_radius": wheel_radius + wheel_radius_error, 
             "wheel_separation": wheel_separation + wheel_separation_error}
        ]
    )


    return [noisy_controller_node]
        
def generate_launch_description():
    return LaunchDescription([
        # Declare Launch Arguments
        DeclareLaunchArgument("wheel_radius", default_value="0.033"),
        DeclareLaunchArgument("wheel_separation", default_value="0.297"), 
        DeclareLaunchArgument("wheel_radius_error", default_value="0.005"),
        DeclareLaunchArgument("wheel_separation_error", default_value="0.02"),
        
        # Spawn ONLY the noisy Python node
        OpaqueFunction(function=launch_noisy_controller)
    ])