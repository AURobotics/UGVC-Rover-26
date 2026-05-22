from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'road_detector'  # Must match your package name

setup(
    name=package_name,  # ROS2 package name
    version='0.0.1',   # Semantic versioning
    packages=find_packages(exclude=['test']),  # Auto-discover Python packages
    
    # DATA FILES - Critical for ROS2
    data_files=[
        # Resource index - tells ROS2 this is a package (there by default)
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        
        # package.xml goes here (there by default)
        ('share/' + package_name, ['package.xml']),
        
        # Launch files directory
        (os.path.join('share', package_name, 'launch'), 
            glob('launch/*.py')),
            
        # Config files directory  
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
        ],
    
    # Dependencies
    install_requires=['setuptools'],
    
    # Package metadata
    zip_safe=True,
    maintainer='abdelaziz',
    maintainer_email='abdelaziz.islam.galal@gmail.com',
    description='TODO: subscribes to video stream, ' \
    'detects white road lane markings and white pot holes' \
    ' then publishes the detected markings and potholes as a point clouds for Nav2',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'road_detector_node = road_detector.road_detector_node:main',
            'video_publisher_node = road_detector.video_publisher_node:main',
            'pointcloud_logger_node = road_detector.pointcloud_logger_node:main',
        ],
    },
)