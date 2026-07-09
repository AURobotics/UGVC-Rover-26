from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'mission'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), 
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abdelaziz',
    maintainer_email='abdelaziz.islam.galal@gmail.com',
    description='State Machine for the mission',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "mission_node=mission.mission_node:main",
            "test_node=mission.test_node:main"
        ],
    },
)
