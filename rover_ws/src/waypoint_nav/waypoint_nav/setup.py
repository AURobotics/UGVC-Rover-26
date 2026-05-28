from setuptools import setup

package_name = 'waypoint_nav'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rowan',
    maintainer_email='rowan@example.com',
    description='waypoint navigation package',
    license='MIT',
    entry_points={
        'console_scripts': [
            'trajectory = waypoint_nav.trajectory:main',
           'controller = waypoint_nav.controller:main', 
       ],
    },
)
