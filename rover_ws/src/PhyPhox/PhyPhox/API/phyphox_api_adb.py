import requests
import json
from typing import List, Dict, Optional, Union
from urllib.parse import quote_plus

# Base URL when using ADB port forwarding
BASE_URL = "http://localhost:8080"


def fetch_sensor_data(sensor_names: Union[str, List[str]]) -> Optional[Dict]:

    url = f"{BASE_URL}/get"
    if isinstance(sensor_names, str):
        query_parts = [quote_plus(sensor_names)]
    else:
        query_parts = [quote_plus(sensor_name) for sensor_name in sensor_names]

    if not query_parts:
        print("No sensor names provided for fetch_sensor_data")
        return None

    url = f"{url}?{'&'.join(query_parts)}"
    
    try:
        # Step 1: Make HTTP GET request using requests library
        response = requests.get(url, timeout=2.0)
        
        # Check for HTTP errors (4xx, 5xx)
        response.raise_for_status()
        
        # Step 2: Parse JSON response using json.loads()
        data = json.loads(response.text)
        
        return data
        
    except requests.exceptions.Timeout:
        print(f"Timeout fetching {sensor_names}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Connection error fetching {sensor_names}. Is ADB port forwarding active?")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {sensor_names}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response for {sensor_name}: {e}")
        return None


def extract_floats(data: Dict, sensor_name: str) -> List[float]:
    
    try:
        # Navigate JSON structure: data['buffer'][sensor_name]['buffer']
        if not data or 'buffer' not in data:
            print(f"Error extracting floats from {sensor_name}: Response missing 'buffer' key")
            print(f"Available keys: {list(data.keys()) if data else 'No data'}")
            return []
        
        if sensor_name not in data['buffer']:
            print(f"Error extracting floats from {sensor_name}: Sensor not found in buffer")
            print(f"Available sensors: {list(data['buffer'].keys())}")
            return []
        
        buffer = data['buffer'][sensor_name]['buffer']
        
        # Convert all values to float, ignoring nulls and non-numeric entries.
        values = []
        for value in buffer:
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        return values
        
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error extracting floats from {sensor_name}: {e}")
        if data:
            print(f"Data structure: {json.dumps(data, indent=2)[:500]}")
        return []


def get_latest_value(sensor_name: str) -> Optional[float]:
    
    data = fetch_sensor_data(sensor_name)
    if data:
        values = extract_floats(data, sensor_name)
        if values:
            return values[-1]  # Last value in buffer is most recent
    return None


def get_all_values(sensor_name: str) -> List[float]:
    
    data = fetch_sensor_data(sensor_name)
    if data:
        return extract_floats(data, sensor_name)
    return []


def get_all_accelerometer() -> Dict[str, float]:
   
    result = {}
    
    for axis, suffix in [('x', 'X'), ('y', 'Y'), ('z', 'Z')]:
        sensor_name = f'acc{suffix}'
        value = get_latest_value(sensor_name)
        result[axis] = value if value is not None else 0.0
    
    return result


def get_all_gyroscope() -> Dict[str, float]:
    
    result = {}
    
    for axis, suffix in [('x', 'X'), ('y', 'Y'), ('z', 'Z')]:
        sensor_name = f'gyr{suffix}'
        value = get_latest_value(sensor_name)
        result[axis] = value if value is not None else 0.0
    
    return result


def get_all_linear_acceleration() -> Dict[str, float]:
    
    result = {}
    
    for axis, suffix in [('x', 'X'), ('y', 'Y'), ('z', 'Z')]:
        sensor_name = f'lin{suffix}'
        value = get_latest_value(sensor_name)
        result[axis] = value if value is not None else 0.0
    
    return result


def get_all_magnetometer() -> Dict[str, float]:
    
    result = {}
    
    for axis, suffix in [('x', 'X'), ('y', 'Y'), ('z', 'Z')]:
        sensor_name = f'mag{suffix}'
        value = get_latest_value(sensor_name)
        result[axis] = value if value is not None else 0.0
    
    return result


def get_gps_location() -> Dict[str, float]:
    
    result = {}
    sensor_mapping = {
        'lat': 'locLat',
        'lon': 'locLon',
        'altitude': 'locZ',
        'velocity': 'locV',
        'direction': 'locDir',
        'accuracy': 'locAccuracy',
        'z_accuracy': 'locZAccuracy',
        'satellites': 'locSatellites',
        'status': 'locStatus'
    }
    
    for key, sensor_name in sensor_mapping.items():
        value = get_latest_value(sensor_name)
        result[key] = value if value is not None else 0.0
    
    return result


def get_all_sensors() -> Dict[str, Dict[str, float]]:
    
    return {
        'accelerometer': get_all_accelerometer(),
        'gyroscope': get_all_gyroscope(),
        'linear_acceleration': get_all_linear_acceleration(),
        'magnetometer': get_all_magnetometer(),
        'location': get_gps_location()
    }


def start_acquisition() -> bool:
    
    url = f"{BASE_URL}/control"
    params = {"cmd": "start"}
    
    try:
        response = requests.get(url, params=params, timeout=2.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def stop_acquisition() -> bool:
    
    url = f"{BASE_URL}/control"
    params = {"cmd": "stop"}
    
    try:
        response = requests.get(url, params=params, timeout=2.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def clear_buffers() -> bool:
    
    url = f"{BASE_URL}/control"
    params = {"cmd": "clear"}
    
    try:
        response = requests.get(url, params=params, timeout=2.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def list_available_sensors() -> List[str]:
    
    try:
        response = requests.get(f"{BASE_URL}/get", timeout=2.0)
        response.raise_for_status()
        data = json.loads(response.text)
        return list(data.get('buffer', {}).keys()) if isinstance(data.get('buffer'), dict) else []
    except requests.exceptions.RequestException as e:
        print(f"Error listing sensors: {e}")
        return []


def test_connection() -> bool:
   
    try:
        response = requests.get(BASE_URL, timeout=2.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False