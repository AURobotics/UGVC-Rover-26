from setuptools import find_packages, setup

package_name = 'pid_navigation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmed-elmasry',
    maintainer_email='ahmedmasry5464222@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lane_pid_node = pid_navigation.lane_pid_node:main',
            'pothole_pid_node = pid_navigation.pothole_pid_node:main',
        ],
    },
)
