from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'lane_detector_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'), glob('models/*')),
        (os.path.join('share', package_name, 'videos'), glob('videos/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yaya',
    maintainer_email='yaya@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
        'lane_detector_node = lane_detector_pkg.lane_detector_node:main',
        'testOfLanes = lane_detector_pkg.testOfLanes:main',
    ],
}
)