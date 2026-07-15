import os
from glob import glob
from setuptools import find_packages, setup 

package_name = 'waypoint_nav'

setup(
    name=package_name,
    version='0.0.0',
    
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rowan',
    maintainer_email='rowanmokhtar6@gmail.com',
    description='waypoint navigation package',
    license='MIT',
    entry_points={
        'console_scripts': [
            'trajectory = waypoint_nav.trajectory:main', #server
            'controller = waypoint_nav.controller:main', #client
        ],
    },
)