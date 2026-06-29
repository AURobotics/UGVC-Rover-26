# Phyphox API Documentation & ROS Integration
## Reverse Engineered from Network Traffic Analysis

**Branch:** PhyPhox  
**Date:** 2026-05-20  
**Connection Method:** ADB Port Forwarding  
**Base URL:** `http://localhost:8080/`  
**Status:** Enhanced with Python API client and ROS integration

---

## Setup

### Prerequisites
```bash
# Install ADB (Android Debug Bridge)
sudo apt install adb  # Linux
brew install android-platform-tools  # Mac

# Enable USB Debugging on phone
# Settings → About Phone → Tap "Build Number" 7 times
# Settings → Developer Options → Enable "USB Debugging"
```

### Port Forwarding
```bash
# Connect phone via USB
adb devices  # Verify phone is connected

# Forward Phyphox port from phone to laptop
adb forward tcp:8080 tcp:8080

# Verify
adb forward --list
# Should show: <device_id> tcp:8080 tcp:8080
```

### Access
- Open Phyphox app on phone
- Enable "Remote Access" (⋮ menu)
- Start measurement (▶ button)
- Access on laptop: http://localhost:8080/

---

## API Endpoints

### 1. Control Commands

| Endpoint | Method | Parameters | Description | Response |
|----------|--------|------------|-------------|----------|
| `/control` | GET | `cmd=start` | Start data acquisition | JSON status |
| `/control` | GET | `cmd=stop` | Stop data acquisition | JSON status |
| `/control` | GET | `cmd=clear` | Clear data buffers | JSON status |

**Example:**
```bash
curl "http://localhost:8080/control?cmd=start"
```

---

### 2. Sensor Data Retrieval

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/get` | GET | `<sensor_name>` | Get sensor data buffer |

**Note:** The API accepts key-only sensor parameters without `=` when there is no timestamp. Multiple sensors can be requested together with `&`, for example `?acc_x&gyr_x&mag_x`.

---

## Sensor Parameters and Data Types

### Accelerometer (with gravity)

| Parameter | Data Type | Unit | Range | Description |
|-----------|-----------|------|-------|-------------|
| `acc_x` | float array | m/s² | ±20 | Acceleration X-axis (includes gravity) |
| `acc_y` | float array | m/s² | ±20 | Acceleration Y-axis (includes gravity) |
| `acc_z` | float array | m/s² | ±20 | Acceleration Z-axis (includes gravity) |

**Example URL:**
```
http://localhost:8080/get?acc_x
http://localhost:8080/get?acc_y
http://localhost:8080/get?acc_z
```
**Chained example:**
```
http://localhost:8080/get?acc_x&gyr_x&mag_x
```

**When phone is flat and still:** `acc_z ≈ 9.8 m/s²` (Earth's gravity)

---

### Gyroscope

| Parameter | Data Type | Unit | Range | Description |
|-----------|-----------|------|-------|-------------|
| `gyr_x` | float array | rad/s | ±35 | Angular velocity X-axis |
| `gyr_y` | float array | rad/s | ±35 | Angular velocity Y-axis |
| `gyr_z` | float array | rad/s | ±35 | Angular velocity Z-axis |

**Example URL:**
```
http://localhost:8080/get?gyr_x=
http://localhost:8080/get?gyr_y=
http://localhost:8080/get?gyr_z=
```

**When phone is still:** All values ≈ 0.0 rad/s

---

### Linear Acceleration (without gravity)

| Parameter | Data Type | Unit | Range | Description |
|-----------|-----------|------|-------|-------------|
| `lin_acc_x` | float array | m/s² | ±20 | Linear acceleration X-axis (gravity removed) |
| `lin_acc_y` | float array | m/s² | ±20 | Linear acceleration Y-axis (gravity removed) |
| `lin_acc_z` | float array | m/s² | ±20 | Linear acceleration Z-axis (gravity removed) |

**Example URL:**
```
http://localhost:8080/get?lin_acc_x=
http://localhost:8080/get?lin_acc_y=
http://localhost:8080/get?lin_acc_z=
```

**When phone is still:** All values ≈ 0.0 m/s² (no motion)

---

### Magnetic Field (Magnetometer)

| Parameter | Data Type | Unit | Range | Description |
|-----------|-----------|------|-------|-------------|
| `mag_x` | float array | µT | ±1000 | Magnetic field X-axis |
| `mag_y` | float array | µT | ±1000 | Magnetic field Y-axis |
| `mag_z` | float array | µT | ±1000 | Magnetic field Z-axis |

**Example URL:**
```
http://localhost:8080/get?mag_x=
http://localhost:8080/get?mag_y=
http://localhost:8080/get?mag_z=
```

**Typical values:** 20-60 µT (Earth's magnetic field)

---

### GPS Location

| Parameter | Data Type | Unit | Range | Description |
|-----------|-----------|------|-------|-------------|
| `lat` | float array | degrees | -90 to 90 | Latitude (North/South) |
| `lon` | float array | degrees | -180 to 180 | Longitude (East/West) |
| `altitude` | float array | meters | varies | Altitude above sea level |

**Example URL:**
```
http://localhost:8080/get?lat=
http://localhost:8080/get?lon=
http://localhost:8080/get?altitude=
```

**Note:** May require outdoor location for GPS fix. Indoor values may be 0.0 or outdated.

---

## Response Format

All sensor data endpoints return JSON in this format:

```json
{
  "buffer": {
    "<sensor_name>": {
      "buffer": [
        value1,
        value2,
        value3,
        ...
      ],
      "size": 500,
      "updateMode": "partial"
    }
  },
  "status": {
    "measuring": true,
    "timedRun": false
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `buffer.<sensor>.buffer` | float[] | Array of sensor readings (oldest to newest) |
| `buffer.<sensor>.size` | int | Maximum buffer size |
| `buffer.<sensor>.updateMode` | string | Update mode ("partial" or "full") |
| `status.measuring` | bool | Whether measurement is currently running |
| `status.timedRun` | bool | Whether this is a timed run |

### Extracting Latest Value

The **last element** in the buffer array is the most recent:

```python
latest_value = data['buffer']['acc_x']['buffer'][-1]
```

---

## Example Responses

### Accelerometer X-axis
**Request:**
```bash
curl "http://localhost:8080/get?acc_x="
```

**Response:**
```json
{
  "buffer": {
    "acc_x": {
      "buffer": [-0.234, -0.198, -0.156, -0.123, 0.012],
      "size": 500,
      "updateMode": "partial"
    }
  },
  "status": {
    "measuring": true,
    "timedRun": false
  }
}
```

### GPS Latitude
**Request:**
```bash
curl "http://localhost:8080/get?lat="
```

**Response:**
```json
{
  "buffer": {
    "lat": {
      "buffer": [30.043611, 30.043612, 30.043610],
      "size": 100,
      "updateMode": "partial"
    }
  },
  "status": {
    "measuring": true,
    "timedRun": false
  }
}
```

---

## URL Observations from Network Tab

### URLs Observed (with timestamps removed)

**Control:**
```
GET http://localhost:8080/control?cmd=start
GET http://localhost:8080/control?cmd=stop
GET http://localhost:8080/control?cmd=clear
```

**Accelerometer:**
```
GET http://localhost:8080/get?acc_x=
GET http://localhost:8080/get?acc_y=
GET http://localhost:8080/get?acc_z=
```

**Gyroscope:**
```
GET http://localhost:8080/get?gyr_x=
GET http://localhost:8080/get?gyr_y=
GET http://localhost:8080/get?gyr_z=
```

**Linear Acceleration:**
```
GET http://localhost:8080/get?lin_acc_x=
GET http://localhost:8080/get?lin_acc_y=
GET http://localhost:8080/get?lin_acc_z=
```

**Magnetometer:**
```
GET http://localhost:8080/get?mag_x=
GET http://localhost:8080/get?mag_y=
GET http://localhost:8080/get?mag_z=
```

**GPS:**
```
GET http://localhost:8080/get?lat=
GET http://localhost:8080/get?lon=
GET http://localhost:8080/get?altitude=
```

### Timestamp Parameters

The web interface often appends timestamps to prevent caching:
```
http://localhost:8080/get?acc_x=&t=1234567890123
                                   ^^^^^^^^^^^^^^^^
                                   Can be ignored
```

These `&t=<timestamp>` parameters can be safely removed. The API works without them.

---

## Data Type Summary

**All sensor values are `float` (IEEE 754 double precision)**

| Sensor Type | Parameters | Data Type | Unit |
|-------------|------------|-----------|------|
| Accelerometer | acc_x, acc_y, acc_z | float | m/s² |
| Gyroscope | gyr_x, gyr_y, gyr_z | float | rad/s |
| Linear Accel | lin_acc_x, lin_acc_y, lin_acc_z | float | m/s² |
| Magnetometer | mag_x, mag_y, mag_z | float | µT |
| GPS | lat, lon | float | degrees |
| GPS | altitude | float | meters |

---

## Python Implementation

### Phyphox API Client (`phyphox_api_adb.py`)

Complete Python client with automatic error handling, HTTP requests, and JSON parsing.

#### Core Functions

**Connection Testing:**
```python
from phyphox_api_adb import test_connection

if test_connection():
    print("✓ Connected to Phyphox")
else:
    print("✗ Connection failed - check ADB forwarding")
```

**Control Functions:**
```python
from phyphox_api_adb import start_acquisition, stop_acquisition, clear_buffers

start_acquisition()   # Start measurement
stop_acquisition()    # Stop measurement
clear_buffers()       # Clear data buffers
```

**Single Sensor Queries:**
```python
from phyphox_api_adb import get_latest_value, get_all_values

# Get most recent value
latest_acc_x = get_latest_value('accX')  # Returns: float or None

# Get all buffered values
all_values = get_all_values('accX')      # Returns: List[float]
```

**Batch Sensor Retrieval (Recommended):**
```python
from phyphox_api_adb import (
    get_all_accelerometer,
    get_all_gyroscope,
    get_all_linear_acceleration,
    get_all_magnetometer,
    get_gps_location,
    get_all_sensors
)

# Individual sensor groups
accel = get_all_accelerometer()  # {'x': float, 'y': float, 'z': float}
gyro = get_all_gyroscope()
lin_accel = get_all_linear_acceleration()
mag = get_all_magnetometer()

# GPS with extended fields
gps = get_gps_location()
# Returns: {
#   'lat': float,
#   'lon': float,
#   'altitude': float,
#   'velocity': float,
#   'direction': float,
#   'accuracy': float,
#   'z_accuracy': float,
#   'satellites': float,
#   'status': float
# }

# Get all sensors at once
all_data = get_all_sensors()
# Returns: {
#   'accelerometer': {...},
#   'gyroscope': {...},
#   'linear_acceleration': {...},
#   'magnetometer': {...},
#   'location': {...}
# }
```

#### Error Handling

The API client includes robust error handling:

```python
# Timeouts (default 2.0s)
# ConnectionError (if ADB forwarding not active)
# JSON parsing errors
# Missing sensor/buffer errors

# All errors are logged with helpful messages
try:
    data = fetch_sensor_data('accX')
except:
    # Check logs for: "Is ADB port forwarding active?"
    pass
```

#### Example: Real-time IMU Monitoring

```python
from phyphox_api_adb import get_all_accelerometer, get_all_gyroscope, test_connection
import time

if not test_connection():
    print("Failed to connect to Phyphox")
    exit()

print("Monitoring IMU data (press Ctrl+C to stop)...")
try:
    while True:
        accel = get_all_accelerometer()
        gyro = get_all_gyroscope()
        
        print(f"\rAccel: X={accel['x']:6.2f} Y={accel['y']:6.2f} Z={accel['z']:6.2f} | "
              f"Gyro: X={gyro['x']:6.2f} Y={gyro['y']:6.2f} Z={gyro['z']:6.2f}", end='')
        
        time.sleep(0.05)  # 20 Hz
except KeyboardInterrupt:
    print("\nStopped")
```

---

### ROS Integration (`phyphox_ros_node_adb.py`)

Full ROS node that publishes Phyphox sensor data to standard ROS topics.

#### ROS Topics Published

| Topic | Message Type | Description |
|-------|-------------|-------------|
| `/phyphox/imu` | `sensor_msgs/Imu` | Accelerometer (with gravity) + Gyroscope |
| `/phyphox/magnetic_field` | `sensor_msgs/MagneticField` | Magnetometer (µT converted to Tesla) |
| `/phyphox/linear_acceleration` | `geometry_msgs/Vector3Stamped` | Linear acceleration (gravity removed) |
| `/phyphox/gps` | `sensor_msgs/NavSatFix` | GPS location and status |

#### ROS Parameters

```yaml
# Node parameters (default values)
~rate: 20.0          # Publishing rate (Hz)
~frame_id: 'phyphox' # TF frame ID
~timeout: 2.0        # HTTP timeout (seconds)
```

#### Launching the ROS Node

**From launch file:**
```xml
<launch>
    <!-- Ensure ADB port forwarding is active -->
    <!-- adb forward tcp:8080 tcp:8080 -->
    
    <node name="phyphox_adb_node" pkg="rover_ws" type="phyphox_ros_node_adb.py" output="screen">
        <param name="rate" value="20"/>
        <param name="frame_id" value="phyphox"/>
        <param name="timeout" value="2.0"/>
    </node>
</launch>
```

**Manually:**
```bash
# In ROS environment
rosrun rover_ws phyphox_ros_node_adb.py
```

#### ROS Node Features

- **Connection Testing:** Validates Phyphox connection on startup
- **Automatic Startup:** Starts data acquisition if not already running
- **Error Recovery:** Graceful handling of connection failures
- **Unit Conversion:** Automatically converts sensor units (µT → T, etc.)
- **Message Headers:** Stamps all messages with ROS timestamps

#### Monitoring ROS Topics

```bash
# View IMU data
rostopic echo /phyphox/imu

# View GPS data
rostopic echo /phyphox/gps

# View magnetic field
rostopic echo /phyphox/magnetic_field

# Monitor publish rate
rostopic hz /phyphox/imu

# Record bag file
rosbag record /phyphox/imu /phyphox/gps -o sensor_data.bag
```

---

## GPS Location Data

The API now provides extended GPS information:

| Field | Unit | Description |
|-------|------|-------------|
| `lat` | degrees | Latitude (North/South) |
| `lon` | degrees | Longitude (East/West) |
| `altitude` | meters | Altitude above sea level |
| `velocity` | m/s | Speed over ground |
| `direction` | degrees | Heading (0-360°) |
| `accuracy` | meters | Horizontal accuracy |
| `z_accuracy` | meters | Vertical accuracy |
| `satellites` | count | Number of satellites used |
| `status` | code | GPS fix status |

**Example:**
```python
from phyphox_api_adb import get_gps_location

gps = get_gps_location()
print(f"Position: {gps['lat']}, {gps['lon']}")
print(f"Accuracy: ±{gps['accuracy']:.1f}m")
print(f"Satellites: {gps['satellites']:.0f}")
```

---

## Advanced Usage

### Custom HTTP Requests

For advanced use cases, access the base URL directly:

```python
import requests
import json

BASE_URL = "http://localhost:8080"

# Get raw response
response = requests.get(f"{BASE_URL}/get?accX=", timeout=2.0)
data = json.loads(response.text)

# Access full buffer info
buffer_size = data['buffer']['accX']['size']
update_mode = data['buffer']['accX']['updateMode']
is_measuring = data['status']['measuring']
```

### Sensor Discovery

```python
from phyphox_api_adb import list_available_sensors

available = list_available_sensors()
print(f"Available sensors: {available}")
```

### Batch Processing

```python
from phyphox_api_adb import fetch_sensor_data, extract_floats

# Low-level access for custom processing
raw_data = fetch_sensor_data('accX')
values = extract_floats(raw_data, 'accX')

# Process values
average = sum(values) / len(values) if values else 0
```

---

## Testing Checklist

### Basic Setup
- [x] ADB port forwarding active (`adb forward tcp:8080 tcp:8080`)
- [x] Phyphox Remote Access enabled
- [x] Can access http://localhost:8080/ in browser
- [x] Device connected via USB

### API Client Testing
- [x] Connection test passes: `test_connection()`
- [x] Acquisition control works: `start_acquisition()`, `stop_acquisition()`
- [x] Single sensor retrieval: `get_latest_value()`, `get_all_values()`
- [x] Batch retrieval works: `get_all_accelerometer()`, etc.
- [x] Error handling for timeout (2.0s)
- [x] Error handling for connection failure
- [x] JSON parsing handles null values
- [x] GPS extended fields available

### ROS Integration Testing
- [x] ROS node starts without errors
- [x] ROS node detects Phyphox connection
- [x] Topics published: `/phyphox/imu`, `/phyphox/gps`, `/phyphox/magnetic_field`
- [x] Message headers stamped with timestamps
- [x] Unit conversions correct (µT → Tesla)
- [x] Publishing rate matches parameter (default 20 Hz)
- [x] Can record topics to bag file
- [x] ROS node gracefully handles disconnection

### Network Debugging
- [x] Browser DevTools network tab open
- [x] All sensor URLs observed
- [x] Timestamp parameters identified
- [x] Response format matches documentation
- [x] No spurious errors in console

---

## Advantages of This Approach

✅ **No WiFi needed** - USB connection only  
✅ **No IP configuration** - Always localhost:8080  
✅ **More reliable** - No network interference  
✅ **Lower latency** - USB is faster than WiFi  
✅ **Simpler setup** - One `adb forward` command  
✅ **Production-ready client** - Full error handling & type safety  
✅ **ROS integration** - Direct integration with ROS ecosystem  
✅ **Extended GPS data** - Velocity, direction, accuracy, satellite count  
✅ **Batch operations** - Get all sensor axes in one call  
✅ **Unit conversion** - Automatic µT→Tesla conversion for magnetic field  

---

## What's New (v2.0)

### Python API Client
- ✨ Robust error handling with timeout & connection detection
- ✨ Type hints for better IDE support
- ✨ Batch retrieval functions (get_all_accelerometer, etc.)
- ✨ Connection testing (test_connection)
- ✨ Buffer control (start, stop, clear acquisition)
- ✨ Sensor discovery (list_available_sensors)
- ✨ Extended GPS data (velocity, direction, accuracy, satellites)

### ROS Node Integration
- ✨ Full ROS node (`phyphox_ros_node_adb.py`)
- ✨ Publishes to standard ROS topics (/phyphox/imu, /phyphox/gps, etc.)
- ✨ Uses ROS parameters for configuration
- ✨ Automatic unit conversion
- ✨ Message timestamping and frame IDs
- ✨ Startup validation and error recovery  

---

## Troubleshooting

### Connection Issues

**"Connection refused" / "Failed to connect to Phyphox"**
- Verify: `adb devices` shows your phone
- Run: `adb forward tcp:8080 tcp:8080`
- Check: Phyphox app has Remote Access enabled (⋮ menu)
- Restart Phyphox app if forwarding was set up before launch

**"Is ADB port forwarding active?"**
- Run: `adb forward --list` (should show tcp:8080 → tcp:8080)
- Reconnect USB if necessary
- Try: `adb kill-server && adb start-server`

### API Client Issues

**"Empty buffers []"**
- Press ▶ (Play) to start measurement in Phyphox
- Wait 1-2 seconds for data accumulation
- Verify sensor is enabled in experiment

**"Invalid JSON response" / "Response missing 'buffer' key"**
- Check that Phyphox is still running
- Verify URL: `curl http://localhost:8080/get?accX=`
- Check browser DevTools network tab for actual response

**"Timeout fetching sensor"**
- Increase timeout parameter (default: 2.0s)
- Check USB connection latency
- Verify Phyphox app is responsive

### ROS Node Issues

**"Failed to connect to Phyphox!" (on node startup)**
- Ensure `adb forward tcp:8080 tcp:8080` is active BEFORE launching ROS node
- Check that Phyphox is running with Remote Access enabled
- Verify connection manually: `python3 -c "from phyphox_api_adb import test_connection; print(test_connection())"`

**No ROS topics being published**
- Check node logs: `rosnode info /phyphox_adb_node`
- Verify topics exist: `rostopic list | grep phyphox`
- Check publishing rate: `rostopic hz /phyphox/imu`

**ROS dependency missing**
```bash
# Install ROS dependencies
rosdep install --from-paths src --ignore-src -r -y

# Or manually install
sudo apt install python3-rospy python3-sensor-msgs python3-geometry-msgs
```

### General Debugging

**adb: command not found**
- Install platform-tools: `sudo apt install adb` (Linux) or `brew install android-platform-tools` (Mac)
- Add to PATH if necessary

**GPS values are 0.0 / outdated**
- Go outdoors or near a window
- Wait 30-60 seconds for GPS fix
- Enable Location permission for Phyphox
- Check status field in GPS data for fix quality

**Sensors returning 0.0**
- Verify sensor is enabled in Phyphox experiment
- Check device orientation (gravity affects accelerometer)
- Try clearing buffers: `clear_buffers()`

### Debug Commands

```bash
# Test Python client
python3 << 'EOF'
from phyphox_api_adb import test_connection, get_all_sensors
print("Connection OK" if test_connection() else "Connection FAILED")
print(get_all_sensors())
EOF

# Test ADB forwarding
adb forward --list

# Monitor ROS node
roslaunch rover_ws phyphox.launch --screen

# Record sensor data
rosbag record /phyphox/imu /phyphox/gps -o phyphox_data.bag
```

---

## References

- **Phyphox Official Website:** https://phyphox.org/
- **Phyphox GitHub:** https://github.com/phyphox/phyphox-android
- **ADB Documentation:** https://developer.android.com/studio/command-line/adb

---

## Contributors

- Robotics Team - Rover Project
- API Reverse engineered: 2026-05-19
- Python client implemented: 2026-05-20
- ROS integration added: 2026-05-20
- Connection method: ADB port forwarding
- Tools used: Chrome DevTools, requests, json, rospy

---

## License

Documentation created for educational/robotics purposes.  
Phyphox is licensed under GNU GPL v3.
