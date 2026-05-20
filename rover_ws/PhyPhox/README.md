# Phyphox API Documentation
## Reverse Engineered from Network Traffic Analysis

**Branch:** PhyPhox  
**Date:** 2026-05-19  
**Connection Method:** ADB Port Forwarding  
**Base URL:** `http://localhost:8080/`

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
| `/get` | GET | `<sensor_name>=` | Get sensor data buffer |

**Note:** Empty parameter value is required (e.g., `acc_x=` not just `acc_x`)

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
http://localhost:8080/get?acc_x=
http://localhost:8080/get?acc_y=
http://localhost:8080/get?acc_z=
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

See `phyphox_api_adb.py` for complete implementation using:
- `requests.get()` for HTTP requests
- `json.loads()` for JSON parsing
- Functions to extract floats into Python lists and dictionaries

**Basic usage:**
```python
import requests
import json

# Fetch sensor data
response = requests.get("http://localhost:8080/get?acc_x=")
data = json.loads(response.text)

# Extract float values
values = data['buffer']['acc_x']['buffer']
latest = values[-1]  # Most recent value

print(f"Latest acc_x: {latest:.3f} m/s²")
```

---

## Testing Checklist

- [x] ADB port forwarding active
- [x] Phyphox Remote Access enabled
- [x] Can access http://localhost:8080/ in browser
- [x] F12 developer tools open
- [x] Network tab recording requests
- [x] Observed URLs for all sensor types
- [x] Timestamps removed from URLs
- [x] Data types identified (all float)
- [x] Response format documented
- [x] Python implementation created
- [x] Test script validates all endpoints

---

## Advantages of This Approach

✅ **No WiFi needed** - USB connection only  
✅ **No IP configuration** - Always localhost:8080  
✅ **More reliable** - No network interference  
✅ **Lower latency** - USB is faster than WiFi  
✅ **Simpler setup** - One `adb forward` command  

---

## Troubleshooting

**"Connection refused"**
- Check Remote Access enabled in Phyphox
- Verify `adb forward` is active: `adb forward --list`
- Restart Phyphox app

**"Empty buffers []"**
- Press ▶ (Play) to start measurement
- Wait 1-2 seconds for data accumulation
- Check sensor is enabled in experiment

**"adb: command not found"**
- Install platform-tools
- Add to PATH

**GPS values are 0.0**
- Go outdoors or near window
- Wait 30-60 seconds for GPS fix
- Enable Location permission for Phyphox

---

## References

- **Phyphox Official Website:** https://phyphox.org/
- **Phyphox GitHub:** https://github.com/phyphox/phyphox-android
- **ADB Documentation:** https://developer.android.com/studio/command-line/adb

---

## Contributors

- Robotics Team - Rover Project
- Reverse engineered: 2026-05-19
- Connection method: ADB port forwarding
- Tools used: Chrome DevTools, requests, json

---

## License

Documentation created for educational/robotics purposes.  
Phyphox is licensed under GNU GPL v3.
