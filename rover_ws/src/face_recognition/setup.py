from setuptools import find_packages, setup
import glob

package_name = 'face_recognition'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/face_recognition/launch', ['launch/face_recognition_launch.py']),
    ],
    package_data={
        'face_recognition': [
            'cv_code/*.onnx',     
            'cv_code/assets/*',     
        ],
    },
    install_requires=['setuptools', 'opencv-contrib-python'],
    zip_safe=True,
    maintainer='Administrator',
    maintainer_email='yassin.awad2006@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'test1_node = face_recognition.test1_node:main',
            'test2_node = face_recognition.test2_node:main',
            'face_recognition_node = face_recognition.face_recognition_node:main',
        ],
    },
)