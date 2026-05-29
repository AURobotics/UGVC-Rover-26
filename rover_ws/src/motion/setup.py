from setuptools import find_packages, setup

package_name = 'motion'

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
    maintainer='habibarezq',
    maintainer_email='habibarezq30@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cmd_mux_node = motion.cmd_mux_node:main',
            'servo_cam_node = motion.servo_cam_node:main',
        ],
    },
)
