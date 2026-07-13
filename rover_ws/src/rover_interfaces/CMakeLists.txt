cmake_minimum_required(VERSION 3.12...3.40)
project(rover_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()


find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)  
find_package(geometry_msgs REQUIRED)  
find_package(nav_msgs REQUIRED)      
find_package(action_msgs REQUIRED)    


# FIX: Group dependencies into a single declaration list
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Speed.msg"
  "msg/WheelVel.msg"
  "msg/RoverStatus.msg"
  "action/GenerateBezierPath.action"
  DEPENDENCIES 
    std_msgs
    geometry_msgs
    nav_msgs
    action_msgs
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()