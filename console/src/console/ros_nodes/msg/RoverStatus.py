# generated from rosidl_generator_py/resource/_idl.py.em
# with input from rover_interfaces:msg\RoverStatus.idl
# generated code does not contain a copyright notice

# This is being done at the module level and not on the instance level to avoid looking
# for the same variable multiple times on each instance. This variable is not supposed to
# change during runtime so it makes sense to only look for it once.
from os import getenv

ros_python_check_fields = getenv('ROS_PYTHON_CHECK_FIELDS', default='')


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

# Member 'imu_calibration'
import numpy  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_RoverStatus(type):
    """Metaclass of message 'RoverStatus'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('rover_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'rover_interfaces.msg.RoverStatus')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__rover_status
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__rover_status
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__rover_status
            cls._TYPE_SUPPORT = module.type_support_msg__msg__rover_status
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__rover_status

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class RoverStatus(metaclass=Metaclass_RoverStatus):
    """Message class 'RoverStatus'."""

    __slots__ = [
        '_header',
        '_battery_voltage_1',
        '_battery_voltage_2',
        '_motor_current_fl',
        '_motor_current_fr',
        '_motor_current_bl',
        '_motor_current_br',
        '_servo_1_angle',
        '_servo_2_angle',
        '_laser_enabled',
        '_led_enabled',
        '_emergency_stop',
        '_imu_calibration',
        '_check_fields',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'battery_voltage_1': 'float',
        'battery_voltage_2': 'float',
        'motor_current_fl': 'float',
        'motor_current_fr': 'float',
        'motor_current_bl': 'float',
        'motor_current_br': 'float',
        'servo_1_angle': 'float',
        'servo_2_angle': 'float',
        'laser_enabled': 'boolean',
        'led_enabled': 'boolean',
        'emergency_stop': 'boolean',
        'imu_calibration': 'uint8[4]',
    }

    # This attribute is used to store an rosidl_parser.definition variable
    # related to the data type of each of the components the message.
    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.Array(rosidl_parser.definition.BasicType('uint8'), 4),  # noqa: E501
    )

    def __init__(self, **kwargs):
        if 'check_fields' in kwargs:
            self._check_fields = kwargs['check_fields']
        else:
            self._check_fields = ros_python_check_fields == '1'
        if self._check_fields:
            assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
                'Invalid arguments passed to constructor: %s' % \
                ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        self.battery_voltage_1 = kwargs.get('battery_voltage_1', float())
        self.battery_voltage_2 = kwargs.get('battery_voltage_2', float())
        self.motor_current_fl = kwargs.get('motor_current_fl', float())
        self.motor_current_fr = kwargs.get('motor_current_fr', float())
        self.motor_current_bl = kwargs.get('motor_current_bl', float())
        self.motor_current_br = kwargs.get('motor_current_br', float())
        self.servo_1_angle = kwargs.get('servo_1_angle', float())
        self.servo_2_angle = kwargs.get('servo_2_angle', float())
        self.laser_enabled = kwargs.get('laser_enabled', bool())
        self.led_enabled = kwargs.get('led_enabled', bool())
        self.emergency_stop = kwargs.get('emergency_stop', bool())
        if 'imu_calibration' not in kwargs:
            self.imu_calibration = numpy.zeros(4, dtype=numpy.uint8)
        else:
            self.imu_calibration = kwargs.get('imu_calibration')

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.get_fields_and_field_types().keys(), self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    if self._check_fields:
                        assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.header != other.header:
            return False
        if self.battery_voltage_1 != other.battery_voltage_1:
            return False
        if self.battery_voltage_2 != other.battery_voltage_2:
            return False
        if self.motor_current_fl != other.motor_current_fl:
            return False
        if self.motor_current_fr != other.motor_current_fr:
            return False
        if self.motor_current_bl != other.motor_current_bl:
            return False
        if self.motor_current_br != other.motor_current_br:
            return False
        if self.servo_1_angle != other.servo_1_angle:
            return False
        if self.servo_2_angle != other.servo_2_angle:
            return False
        if self.laser_enabled != other.laser_enabled:
            return False
        if self.led_enabled != other.led_enabled:
            return False
        if self.emergency_stop != other.emergency_stop:
            return False
        if any(self.imu_calibration != other.imu_calibration):
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def header(self):
        """Message field 'header'."""
        return self._header

    @header.setter
    def header(self, value):
        if self._check_fields:
            from std_msgs.msg import Header
            assert \
                isinstance(value, Header), \
                "The 'header' field must be a sub message of type 'Header'"
        self._header = value

    @builtins.property
    def battery_voltage_1(self):
        """Message field 'battery_voltage_1'."""
        return self._battery_voltage_1

    @battery_voltage_1.setter
    def battery_voltage_1(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'battery_voltage_1' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'battery_voltage_1' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._battery_voltage_1 = value

    @builtins.property
    def battery_voltage_2(self):
        """Message field 'battery_voltage_2'."""
        return self._battery_voltage_2

    @battery_voltage_2.setter
    def battery_voltage_2(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'battery_voltage_2' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'battery_voltage_2' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._battery_voltage_2 = value

    @builtins.property
    def motor_current_fl(self):
        """Message field 'motor_current_fl'."""
        return self._motor_current_fl

    @motor_current_fl.setter
    def motor_current_fl(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'motor_current_fl' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'motor_current_fl' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._motor_current_fl = value

    @builtins.property
    def motor_current_fr(self):
        """Message field 'motor_current_fr'."""
        return self._motor_current_fr

    @motor_current_fr.setter
    def motor_current_fr(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'motor_current_fr' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'motor_current_fr' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._motor_current_fr = value

    @builtins.property
    def motor_current_bl(self):
        """Message field 'motor_current_bl'."""
        return self._motor_current_bl

    @motor_current_bl.setter
    def motor_current_bl(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'motor_current_bl' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'motor_current_bl' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._motor_current_bl = value

    @builtins.property
    def motor_current_br(self):
        """Message field 'motor_current_br'."""
        return self._motor_current_br

    @motor_current_br.setter
    def motor_current_br(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'motor_current_br' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'motor_current_br' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._motor_current_br = value

    @builtins.property
    def servo_1_angle(self):
        """Message field 'servo_1_angle'."""
        return self._servo_1_angle

    @servo_1_angle.setter
    def servo_1_angle(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'servo_1_angle' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'servo_1_angle' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._servo_1_angle = value

    @builtins.property
    def servo_2_angle(self):
        """Message field 'servo_2_angle'."""
        return self._servo_2_angle

    @servo_2_angle.setter
    def servo_2_angle(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'servo_2_angle' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'servo_2_angle' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._servo_2_angle = value

    @builtins.property
    def laser_enabled(self):
        """Message field 'laser_enabled'."""
        return self._laser_enabled

    @laser_enabled.setter
    def laser_enabled(self, value):
        if self._check_fields:
            assert \
                isinstance(value, bool), \
                "The 'laser_enabled' field must be of type 'bool'"
        self._laser_enabled = value

    @builtins.property
    def led_enabled(self):
        """Message field 'led_enabled'."""
        return self._led_enabled

    @led_enabled.setter
    def led_enabled(self, value):
        if self._check_fields:
            assert \
                isinstance(value, bool), \
                "The 'led_enabled' field must be of type 'bool'"
        self._led_enabled = value

    @builtins.property
    def emergency_stop(self):
        """Message field 'emergency_stop'."""
        return self._emergency_stop

    @emergency_stop.setter
    def emergency_stop(self, value):
        if self._check_fields:
            assert \
                isinstance(value, bool), \
                "The 'emergency_stop' field must be of type 'bool'"
        self._emergency_stop = value

    @builtins.property
    def imu_calibration(self):
        """Message field 'imu_calibration'."""
        return self._imu_calibration

    @imu_calibration.setter
    def imu_calibration(self, value):
        if self._check_fields:
            if isinstance(value, numpy.ndarray):
                assert value.dtype == numpy.uint8, \
                    "The 'imu_calibration' numpy.ndarray() must have the dtype of 'numpy.uint8'"
                assert value.size == 4, \
                    "The 'imu_calibration' numpy.ndarray() must have a size of 4"
                self._imu_calibration = value
                return
            from collections.abc import Sequence
            from collections.abc import Set
            from collections import UserList
            from collections import UserString
            assert \
                ((isinstance(value, Sequence) or
                  isinstance(value, Set) or
                  isinstance(value, UserList)) and
                 not isinstance(value, str) and
                 not isinstance(value, UserString) and
                 len(value) == 4 and
                 all(isinstance(v, int) for v in value) and
                 all(val >= 0 and val < 256 for val in value)), \
                "The 'imu_calibration' field must be a set or sequence with length 4 and each value of type 'int' and each unsigned integer in [0, 255]"
        self._imu_calibration = numpy.array(value, dtype=numpy.uint8)
