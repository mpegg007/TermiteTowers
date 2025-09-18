# ESP32 Node01 Sensor Setup

## Overview
Multi-sensor ESP32 node for comprehensive monitoring including environmental sensors, motion detection, audio monitoring, and light detection. This is the primary test bed device with every imaginable sensor (formerly known as green-room/orion).

## Hardware Components

### Microcontroller
- **ESP32 Dev Board** (Elegoo ESP32)
- **Power**: 3.3V/5V via USB or external supply

### Environmental Sensors (I2C Bus)
- **BMP280**: Temperature + Atmospheric Pressure
- **SHT3x**: Temperature + Humidity (dual temperature for accuracy)

### Motion Detection
- **S3KM1110**: 24GHz mmWave radar (UART + GPIO)
  - Uses FMCW (Frequency Modulated Continuous Wave) technology
  - Detects human presence and micro-movements (breathing/heartbeat)
- **PIR Sensor**: Traditional infrared motion detection (3-wire)

### Audio Monitoring
- **INMP441**: Digital I2S omnidirectional microphone
  - Professional-grade digital audio input
  - Voice assistant capability

### Distance & Light Detection
- **HC-SR04**: Ultrasonic distance sensor
- **RGB Light Detector**: 3-channel light sensor (Red, Green, Blue)

## Pin Configuration

### I2C Bus (Shared)
```
GPIO21 (SDA) → BMP280, SHT3x SDA pins
GPIO22 (SCL) → BMP280, SHT3x SCL pins
```

### I2S Interface (INMP441 Digital Microphone)
```
GPIO25 (WS)  → INMP441 WS pin (Word Select)
GPIO26 (SCK) → INMP441 SCK pin (Serial Clock)
GPIO27 (SD)  → INMP441 SD pin (Serial Data)
```

### UART2 Interface (S3KM1110 mmWave Radar)
```
GPIO16 (RX2) → S3KM1110 TX pin
GPIO17 (TX2) → S3KM1110 RX pin
GPIO18       → S3KM1110 OT2 pin (optional control)
```

### Digital Pins
```
GPIO13 → HC-SR04 Echo
GPIO14 → HC-SR04 Trigger
GPIO19 → PIR Motion Sensor OUT
```

### Analog Pins (RGB Light Detector)
```
GPIO32 → Light Detector Red Channel
GPIO33 → Light Detector Green Channel
GPIO35 → Light Detector Blue Channel
```

### Power Connections
```
3.3V → All sensor VCC pins
GND  → All sensor GND pins
```

## I2C Device Addresses
```
BMP280: 0x76 (or 0x77)
SHT3x:  0x44 (or 0x45)
```

## ESPHome Sensors & Entities

### Environmental Monitoring
- `sensor.green_room_bmp_temperature` - BMP280 temperature
- `sensor.green_room_sht_temperature` - SHT3x temperature
- `sensor.green_room_pressure` - Atmospheric pressure
- `sensor.green_room_humidity` - Humidity level

### Motion Detection
- `binary_sensor.green_room_mmwave_presence` - mmWave radar presence
- `binary_sensor.green_room_pir_motion` - PIR motion detection
- `binary_sensor.green_room_any_motion` - Combined motion (either sensor)

### Audio Monitoring
- `binary_sensor.green_room_audio_detected` - Audio activity detection
- `sensor.green_room_sound_activity` - Audio activity percentage (0-100%)

### Distance & Light
- `sensor.green_room_distance` - Ultrasonic distance measurement
- `sensor.green_room_light_red` - Red light channel (V)
- `sensor.green_room_light_green` - Green light channel (V)
- `sensor.green_room_light_blue` - Blue light channel (V)
- `sensor.green_room_light_level` - Calculated total light level (lux)

## Key Features

### Multi-Technology Motion Detection
- **mmWave Radar**: Detects presence even when stationary (breathing/heartbeat)
- **PIR Sensor**: Traditional motion detection for larger movements
- **Combined Detection**: "Any Motion" entity triggers on either sensor

### Dual Temperature Sensing
- **BMP280**: Environmental temperature + pressure
- **SHT3x**: Precision temperature + humidity
- Provides redundancy and cross-validation

### Professional Audio Detection
- **I2S Digital Microphone**: High-quality audio input
- **Voice Assistant Integration**: Real-time audio activity detection
- **No Fake Readings**: Actual sound detection based on microphone input

### RGB Light Analysis
- **Individual Channels**: Separate red, green, blue readings
- **Calculated Lux**: Approximate total light level
- **Color Temperature**: Potential for color analysis

## Communication Protocols Used
- **I2C**: Environmental sensors (BMP280, SHT3x)
- **I2S**: Digital audio (INMP441)
- **UART2**: mmWave radar communication (115200 baud)
- **GPIO**: Motion sensors, distance sensor, light detector

## Automation Potential

### Home Assistant Integration
- Room occupancy detection (multiple methods)
- Environmental monitoring and alerts
- Audio-triggered automations
- Light-based scene control
- Distance-based proximity detection

### Example Use Cases
- Automatic lighting based on presence + light level
- Climate control based on environmental readings
- Security monitoring with multi-sensor motion detection
- Audio-reactive lighting or notifications
- Room utilization tracking

## Technical Notes

### UART Configuration
- **UART2** used for S3KM1110 to keep UART0 free for programming
- **Debug mode enabled** to monitor mmWave radar data
- **115200 baud rate** for reliable communication

### Voice Assistant
- Configured for audio activity detection
- Can be extended for voice commands
- Updates sound activity sensor in real-time

### Sensor Update Intervals
- **Environmental**: 30 seconds (temperature, humidity, pressure)
- **Motion**: Real-time with debounce filters
- **Audio**: 1 second activity updates
- **Distance**: 2 seconds
- **Light**: 2 seconds

## Troubleshooting

### Common Issues
1. **mmWave sensor not responding**: Check UART wiring and power
2. **I2C sensors not detected**: Verify SDA/SCL connections and addresses
3. **Audio not detecting**: Check I2S wiring and microphone power
4. **Motion sensors false triggers**: Adjust filter timing in config

### Debug Tools
- **UART debug enabled** for mmWave sensor data
- **I2C scan enabled** to detect connected devices
- **ESPHome logs** show real-time sensor status

## File Location
Configuration file: `esp32-orion.yaml`
Documentation: `ESP32-Orion-Setup.md`

---
*Last updated: September 14, 2025*
