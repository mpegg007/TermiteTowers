# ESP32 Node02 Sensor Setup

## Overview
Advanced multi-sensor ESP32 node featuring dual audio detection systems, professional light sensing, environmental monitoring, and comprehensive motion detection. This is the secondary test bed device for sensor development in bedroom (formerly known as breakout-board/hydra).

## Hardware Components

### Microcontroller
- **ESP32 Dev Board** (Elegoo ESP32)
- **Power**: 3.3V/5V via USB or external supply

### Environmental Sensors (I2C Bus)
- **SHT3x**: Temperature + Humidity

### Air Quality Sensor
- **DSM501A**: Dust/Particle sensor
  - Detects particles > 1μm and > 2.5μm
  - PM1.0 and PM2.5 measurements
  - 5-wire connection (VCC, GND, Vout1, Vout2, Control)

### Motion Detection
- **PIR Sensor**: Traditional infrared motion detection (3-wire)

### Dual Audio System
- **INMP441**: Digital I2S omnidirectional microphone
  - Professional-grade digital audio input
  - Voice assistant capability
- **KY-037**: Analog sound detection module
  - Digital threshold trigger
  - Analog sound level measurement
  - Adjustable sensitivity potentiometer

### Distance & Light Detection
- **HC-SR04**: Ultrasonic distance sensor
- **BH1750**: Professional digital light sensor (I2C)
  - Wide range: 1-65535 lux
  - High accuracy: ±20% typical
  - Temperature compensated

## Pin Configuration

### I2C Bus (Shared)
```
GPIO21 (SDA) → SHT3x, BH1750 SDA pins
GPIO22 (SCL) → SHT3x, BH1750 SCL pins
```

### I2S Interface (INMP441 Digital Microphone)
```
GPIO25 (WS)  → INMP441 WS pin (Word Select)
GPIO26 (SCK) → INMP441 SCK pin (Serial Clock)
GPIO27 (SD)  → INMP441 SD pin (Serial Data)
```

### Digital Pins
```
GPIO13 → HC-SR04 Echo
GPIO14 → HC-SR04 Trigger
GPIO16 → DSM501A Vout1 (particles > 1μm)
GPIO17 → DSM501A Vout2 (particles > 2.5μm)
GPIO19 → PIR Motion Sensor OUT
GPIO32 → KY-037 Digital Output (DO)
```

### Analog Pin
```
GPIO33 → KY-037 Analog Output (AO)
```

### Available Pins
```
GPIO18 → Available for DSM501A Control (optional)
GPIO35 → Available for future expansion
```

### Power Connections
```
3.3V → SHT3x, BH1750, INMP441, PIR, KY-037 VCC pins
5V   → DSM501A VCC pin (requires 5V for proper operation)
GND  → All sensor GND pins
```

### Power Connections
```
3.3V → All sensor VCC pins
GND  → All sensor GND pins
```

## I2C Device Addresses
```
SHT3x:  0x44 (or 0x45)
BH1750: 0x23 (or 0x5C if ADDR pin high)
```

## ESPHome Sensors & Entities

### Environmental Monitoring
- `sensor.breakout_board_sht_temperature` - SHT3x temperature
- `sensor.breakout_board_humidity` - Humidity level

### Air Quality Monitoring
- `sensor.breakout_board_pm1_0` - PM1.0 particles (μg/m³)
- `sensor.breakout_board_pm2_5` - PM2.5 particles (μg/m³)

### Motion Detection
- `binary_sensor.breakout_board_pir_motion` - PIR motion detection

### Dual Audio System
- `binary_sensor.breakout_board_audio_detected` - INMP441 audio activity
- `sensor.breakout_board_sound_activity` - INMP441 activity percentage (0-100%)
- `binary_sensor.breakout_board_sound_trigger` - KY-037 digital threshold
- `sensor.breakout_board_sound_level` - KY-037 analog voltage (V)
- `sensor.breakout_board_sound_percentage` - KY-037 sound level (0-100%)

### Distance & Light
- `sensor.breakout_board_distance` - Ultrasonic distance measurement
- `sensor.breakout_board_light_level` - BH1750 professional light reading (lux)

## Key Features

### Professional Light Sensing
- **BH1750**: Industry-standard light sensor
- **Wide Dynamic Range**: 1-65535 lux
- **High Accuracy**: ±20% typical across range
- **Temperature Compensation**: Built-in correction
- **Multiple Resolutions**: 0.5, 1.0, or 4.0 lx (configured for 4.0 lx)

### Dual Audio Detection System
- **INMP441**: Professional microphone with voice assistant integration
- **KY-037**: Simple analog sound detection with adjustable threshold
- **Complementary**: Digital precision + analog simplicity
- **Redundant**: Multiple detection methods for reliability

### Single Motion Detection
- **PIR Sensor**: Traditional motion detection for movements
- **Simple & Reliable**: Well-established infrared technology

### Single Temperature Sensing
- **SHT3x**: Precision temperature + humidity sensor
- **All-in-one**: Combined environmental monitoring

## Communication Protocols Used
- **I2C**: Environmental sensor + light sensor (SHT3x, BH1750)
- **I2S**: Professional digital audio (INMP441)
- **GPIO**: Motion sensor, distance sensor, KY-037 digital
- **ADC**: KY-037 analog sound level
- **Duty Cycle**: DSM501A air quality sensor readings

## Sensor Specifications

### DSM501A Air Quality Sensor
- **Detection Range**: Particles 0.5-10μm
- **Output 1 (Vout1)**: Particles > 1.0μm
- **Output 2 (Vout2)**: Particles > 2.5μm
- **Power**: 5V DC (90mA typical)
- **Method**: Duty cycle output proportional to particle concentration
- **Update**: Every 30 seconds
- **Warm-up Time**: ~1 minute for stable readings

### BH1750 Light Sensor
- **Range**: 1 - 65535 lux
- **Accuracy**: ±20%
- **Interface**: I2C
- **Update**: Every 10 seconds
- **Resolution**: Dynamically calculated (optimal)

### KY-037 Sound Module
- **Digital Output**: Adjustable threshold trigger
- **Analog Output**: 0-3.3V sound level
- **Sensitivity**: Adjustable via onboard potentiometer
- **Update Rate**: 500ms for analog readings

### Voice Assistant Audio
- **INMP441**: Professional I2S microphone
- **Voice Detection**: Real-time activity percentage
- **States**: 0% (silent), 50% (listening), 100% (voice detected)

## Automation Potential

### Home Assistant Integration
- **Motion Detection**: PIR-based occupancy detection
- **Environmental Monitoring**: Temperature and humidity
- **Professional Light Control**: Accurate lux-based automation
- **Dual Audio Triggers**: Voice + sound threshold detection
- **Distance-Based Actions**: Proximity automation

### Example Use Cases
- **Smart Lighting**: BH1750 lux-based dimming with PIR motion detection
- **Climate Control**: Temperature + humidity monitoring
- **Audio Monitoring**: Dual microphone system for voice and sound
- **Voice Control**: INMP441 voice assistant integration
- **Sound Detection**: KY-037 noise level tracking
- **Distance Sensing**: HC-SR04 proximity detection

## Technical Notes

### Audio System Architecture
- **INMP441**: High-quality voice detection and assistant
- **KY-037**: Simple sound level monitoring and threshold alerts
- **Independent Operation**: Both systems work simultaneously
- **Different Purposes**: Voice vs. ambient sound monitoring

### Light Sensor Advantages
- **BH1750 vs. Analog**: Digital I2C vs. analog voltage reading
- **Professional Grade**: Industry-standard sensor
- **Wide Range**: Handles bright sunlight to dim indoor lighting
- **No Calibration**: Factory calibrated, ready to use

### UART Configuration
- **No UART used** - GPIO16, GPIO17, GPIO18 now available for expansion
- **Simplified wiring** - fewer connections needed

### Sensor Update Intervals
- **Environmental**: 30 seconds (temperature, humidity)
- **Motion**: Real-time with debounce filters
- **Audio**: 500ms-1s for different components
- **Distance**: 2 seconds
- **Light**: 10 seconds (BH1750 measurement time)

## Pin Utilization
- **Used Pins**: GPIO13, 14, 19, 21, 22, 25, 26, 27, 32, 33
- **Available**: GPIO16, 17, 18, 35 + others for expansion
- **Simplified Layout**: Focused on core functionality

## Troubleshooting

### Common Issues
1. **BH1750 not detected**: Check I2C wiring and ADDR pin connection
2. **KY-037 always triggered**: Adjust sensitivity potentiometer
3. **mmWave sensor not responding**: Check UART wiring and power
4. **Audio systems conflicting**: They operate independently, check individual configs

### Debug Tools
- **UART debug enabled** for mmWave sensor data
- **I2C scan enabled** to detect connected devices
- **ESPHome logs** show real-time sensor status
- **Template sensors** for calculated values verification

## File Locations
- Configuration: `esp32-hydra.yaml`
- Documentation: `ESP32-Hydra-Setup.md`

---
*Last updated: September 16, 2025*
