from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'cameras'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
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
        # (os.path.join('share', package_name, 'config'),
        #     glob('config/*.yaml')),
        ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abdelaziz',
    maintainer_email='abdelaziz.islam.galal@gmail.com',
    description='TODO: publish camera stream',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'external_camera_node = cameras.external_camera_node:main',
            'internal_camera_node = cameras.internal_camera_node:main',
            'viewer_node = cameras.viewer_node:main',
        ],
    },
)
