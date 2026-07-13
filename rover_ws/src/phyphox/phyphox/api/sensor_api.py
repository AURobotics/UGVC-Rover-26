from __future__ import annotations
import requests
import json
from urllib.parse import quote_plus
from enum import Enum
from typing import Literal, overload, Any
from dataclasses import dataclass, fields

@dataclass(frozen=True)
class AccelerometerData:
    accX: float; accY: float; accZ: float

@dataclass(frozen=True)
class GyroscopeData:
    gyrX: float; gyrY: float; gyrZ: float

@dataclass(frozen=True)
class LinearAccelerationData:
    linX: float; linY: float; linZ: float

@dataclass(frozen=True)
class MagneticFieldData:
    magX: float; magY: float; magZ: float

@dataclass(frozen=True)
class LocationData:
    locLat: float; locLon: float; locZ: float; locV: float; locDir: float
    locAccuracy: float; locZAccuracy: float; locStatus: int; locSatellites: int


class SensorType(Enum):
    ACCELEROMETER = AccelerometerData
    GYROSCOPE = GyroscopeData
    LINEAR_ACCELERATION = LinearAccelerationData
    MAGNETIC_FIELD = MagneticFieldData
    LOCATION = LocationData

    @classmethod
    def from_string(cls, name: str) -> "SensorType | None":
        """Maps an incoming string (like 'linear_acceleration') to its Enum variant."""
        # Converts 'linear_acceleration' -> 'LINEAR_ACCELERATION' to match enum names
        normalized = name.strip().upper()
        return cls.__members__.get(normalized)
        
    @property
    def api_key(self) -> str:
        """Returns the lower-case string name for API requests."""
        return self.name.lower()


class SensorServer:
    def __init__(self, port: int = 8080, server_address: str = "http://localhost") -> None:
        self.port = port
        self.server_address = server_address
        self.session = requests.Session()

    @property
    def _base_url(self) -> str:
        return f'{self.server_address}:{self.port}'
    
    @property
    def server_alive(self) -> bool:
        try:
            response = self.session.get(self._base_url, timeout=0.1)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    @property
    def acquisition_is_on(self) -> bool:
        try:
            response = self.session.get(f'{self._base_url}/get')
            response.raise_for_status()
            data = json.loads(response.content)
            status = data.get('status')
            return status is not None and status.get('measuring')
        except requests.exceptions.RequestException as e:
            print(f'Error obtaining data acqusition status: {e}')
            return False
    
    def start_acquisition(self) -> None:
        self.session.get(f'{self._base_url}/control?cmd=start')
    
    def stop_acquisition(self) -> None:
        self.session.get(f'{self._base_url}/control?cmd=stop')
    
        
    @property
    def sensors(self) -> set[SensorType]:
        """Fetches active configuration and returns a set of strongly-typed SensorType enums."""
        try:
            response = self.session.get(f'{self._base_url}/config', timeout=0.1)
            response.raise_for_status()
            data = json.loads(response.content)
            resp_buffers = data.get('inputs')
            
            if not isinstance(resp_buffers, list):
                return set()
            
            active_sensors = set()
            for buffer in resp_buffers:
                source_str = buffer.get('source')
                if source_str:
                    sensor_enum = SensorType.from_string(source_str)
                    if sensor_enum:
                        active_sensors.add(sensor_enum)
                    
            return active_sensors
            
        except requests.exceptions.RequestException as e:
            print(f"Error listing sensors: {e}")
            return set()
    
    @overload
    def get_sensor_data(self, sensor: Literal[SensorType.ACCELEROMETER]) -> AccelerometerData | None: ...
    @overload
    def get_sensor_data(self, sensor: Literal[SensorType.GYROSCOPE]) -> GyroscopeData | None: ...
    @overload
    def get_sensor_data(self, sensor: Literal[SensorType.LINEAR_ACCELERATION]) -> LinearAccelerationData | None: ...
    @overload
    def get_sensor_data(self, sensor: Literal[SensorType.MAGNETIC_FIELD]) -> MagneticFieldData | None: ...
    @overload
    def get_sensor_data(self, sensor: Literal[SensorType.LOCATION]) -> LocationData | None: ...

    def get_sensor_data(self, sensor: SensorType) -> Any:
        sensor_fields = fields(sensor.value)
        field_names = [field.name for field in sensor_fields]

        url = f"{self._base_url}/get?{'&'.join(field_names)}"

        try:
            response = self.session.get(url, timeout=0.1)
            response.raise_for_status()
            data = json.loads(response.text)
            
            buffer_data = data.get('buffer', {})
            extracted_fields = {}
            for field in field_names:
                field_info = buffer_data.get(field, {})
                inner_buffer = field_info.get('buffer', [])
                if inner_buffer:
                    extracted_fields[field] = inner_buffer[0]
                else:
                    return None
            if not extracted_fields:
                return None
            
            return sensor.value(**extracted_fields)
        except Exception as ex:
            print(f'Exception while fetching sensor data: {ex}')
            return None
        
    def get_sensors_data(self, sensors: list[SensorType]) -> dict[SensorType, Any]:
        """Fetches data for multiple sensors in a single, efficient HTTP call."""
        all_field_names = []
        sensor_to_fields = {}
        
        for s in sensors:
            sensor_fields = fields(s.value)
            field_names = [field.name for field in sensor_fields]
            all_field_names.extend(field_names)
            sensor_to_fields[s] = field_names

        url = f"{self._base_url}/get?{'&'.join(all_field_names)}"
        results = {}

        try:
            response = self.session.get(url, timeout=0.1)
            response.raise_for_status()
            data = json.loads(response.text)
            
            buffer_data = data.get('buffer', {})
            
            for s in sensors:
                extracted_fields = {}
                for field in sensor_to_fields[s]:
                    field_info = buffer_data.get(field, {})
                    inner_buffer = field_info.get('buffer', [])
                    if inner_buffer:
                        extracted_fields[field] = inner_buffer[0]
                    else:
                        break
                
                if len(extracted_fields) == len(sensor_to_fields[s]) and extracted_fields:
                    results[s] = s.value(**extracted_fields)
                else:
                    results[s] = None
                    
            return results
            
        except Exception as ex:
            print(f'Exception while fetching combined sensor data: {ex}')
            return {s: None for s in sensors}