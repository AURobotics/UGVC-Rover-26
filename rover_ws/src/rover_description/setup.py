from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rover_description'

def get_files(directory, destination):
    """Recursively get all files preserving subdirectory structure."""
    paths = []
    for (path, _, filenames) in os.walk(directory):
        if filenames:
            dest = os.path.join('share', package_name, destination,
                                os.path.relpath(path, directory))
            paths.append((dest, [os.path.join(path, f) for f in filenames]))
    return paths

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # Config files
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        # URDF files
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        # World files
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*')),
        # Gazebo model files
        *get_files('../gz_model', 'gz_model'),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='habibarezq',
    maintainer_email='habibarezq30@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [],
    },
)