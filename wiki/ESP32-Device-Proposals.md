<!--||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
||  %ccm_git_repo: TermiteTowers %
||  %ccm_git_branch: dev1 %
||  %ccm_git_object_id: wiki/ESP32-Device-Proposals.md:136 %
||  %ccm_git_author: Matthew Pegg %
||  %ccm_git_author_email: mpegg@hotmail.com %
||  %ccm_git_blob_sha: 402660be656ba8571ffbe8cfb53ff17bd2d1d62b %
||  %ccm_git_commit_id: bc247a4e65bdd9936cbca62c9b8ae30ec02c3198 %
||  %ccm_git_commit_count: 136 %
||  %ccm_git_commit_date: 2026-03-01 12:34:10 -0500 %
||  %ccm_git_commit_author: Matthew Pegg %
||  %ccm_git_commit_email: mpegg@hotmail.com %
||  %ccm_git_commit_message: flaresolver startup script fix %
||  %ccm_git_modify_date: 2026-03-01 12:34:16 %
||  %ccm_git_file_last_modified: 2026-03-01 12:34:16 %
||  %ccm_git_file_name: ESP32-Device-Proposals.md %
||  %ccm_git_path: wiki/ESP32-Device-Proposals.md %
||  %ccm_git_language_mode: markdown %
||  %ccm_git_file_type: text/plain %
||  %ccm_git_file_encoding: utf-8 %
||  %ccm_git_file_eol: CRLF %
||  %ccm_git_exec: no %
||  %ccm_git_size: 9980 %
||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
|| ##COMMIT_HISTORY: %git_commit_history: $DATE $AUTHOR $MESSAGE % -->
# ESP32 Device Proposals

This document outlines proposed ESP32 devices for the TermiteTowers smart home infrastructure, including sensor requirements, technical specifications, and implementation plans.

## Overview

The TermiteTowers ESP32 fleet follows the [constellation naming convention](../hams/esphome/ESP32-Naming-Standard.md) and uses standardized sensor configurations for consistency and maintainability.

## Proposed Devices

### 1. ESP32 Apollo - Front Entry Sensor Hub ⭐ **Priority**

**Proposed Name**: `esp32-apollo` (suitable for solar/light-based applications)  
**Location**: Front entry area  
**Primary Purpose**: Comprehensive entry monitoring and environmental sensing

#### Sensor Requirements

| Sensor Type | Model/Specification | Purpose | Accuracy/Range |
|-------------|--------------------|---------|--------------| 
| **Temperature** | SHT30/SHT40 | Environmental monitoring | ±0.2°C |
| **Humidity** | SHT30/SHT40 | Environmental monitoring | ±2% RH |
| **Pressure** | BMP280/BMP390 | Weather monitoring | ±0.12 hPa |
| **Light** | BH1750 or RGB photodiodes | Ambient light detection | 1-65535 lux |
| **PIR Motion** | HC-SR501 or AM312 | Human presence detection | 3-7m range |
| **Ultrasonic Distance** | **JSN-SR04T** or **A02YYUW** | Distance to front door | **±1mm accuracy** |

#### Technical Specifications

```yaml
# Proposed configuration structure
esphome:
  name: esp32-apollo
  friendly_name: "ESP32 Apollo - Front Entry"

# Key sensors configuration
sensor:
  # Environmental cluster
  - platform: sht3xd          # Temp/Humidity
  - platform: bmp280_i2c      # Pressure  
  - platform: bh1750          # Light (I2C)
  
  # Precision distance sensor
  - platform: ultrasonic      # JSN-SR04T waterproof variant
    # Alternative: UART-based A02YYUW for higher accuracy
    
binary_sensor:
  - platform: gpio            # PIR motion detection
```

#### Pin Assignment (Preliminary)

| Pin | Function | Sensor/Component |
|-----|----------|------------------|
| GPIO21 | I2C SDA | SHT30, BMP280, BH1750 |
| GPIO22 | I2C SCL | SHT30, BMP280, BH1750 |
| GPIO14 | Trigger | Ultrasonic sensor |
| GPIO13 | Echo | Ultrasonic sensor |
| GPIO18 | Digital Input | PIR motion sensor |
| GPIO16/17 | UART RX/TX | Alternative for A02YYUW |

#### Implementation Priority: **HIGH**
- **Timeline**: Next available ESP32 board
- **Complexity**: Medium (standard sensors, well-documented)
- **Dependencies**: None (all sensors are common/available)

---

### 2. ESP32 Vega - Garage Door Monitor

**Proposed Name**: `esp32-vega` (bright/prominent applications)  
**Location**: Garage area  
**Primary Purpose**: Garage door monitoring and vehicle detection

#### Sensor Requirements
- **Distance sensor**: Door position monitoring
- **Vibration sensor**: Door operation detection  
- **PIR motion**: Vehicle/person detection
- **Temperature**: Garage climate monitoring
- **Magnetic reed switch**: Door fully closed confirmation

---

### 3. ESP32 Polaris - Garden Weather Station

**Proposed Name**: `esp32-polaris` (navigation/reference device)  
**Location**: Garden/outdoor area  
**Primary Purpose**: Comprehensive weather monitoring

#### Sensor Requirements
- **Temperature/Humidity**: Weatherproof SHT30
- **Pressure**: BMP390 for weather prediction
- **UV sensor**: VEML6070 for sun exposure
- **Rain sensor**: Capacitive or tipping bucket
- **Wind speed/direction**: Anemometer interface
- **Soil moisture**: Capacitive soil sensors

---

### 4. ESP32 Boiler Room - Environmental & Relay Control ⭐ **Priority**

**Proposed Name**: `esp32-boiler`
**Location**: Boiler Room
**Primary Purpose**: Environmental monitoring and relay control for boiler systems

#### Sensor & Actuator Requirements
| Type         | Model/Specification      | Purpose                        |
|--------------|-------------------------|--------------------------------|
| Temperature  | SHT3x (I2C, addr 0x44)  | Boiler room temperature        |
| Humidity     | SHT3x (I2C, addr 0x44)  | Boiler room humidity           |
| Relay Output | Sainsmart 8-Relay GPIOs | Control boiler/aux devices     |

#### Technical Specifications
```yaml
esphome:
  name: esp32-boiler
  friendly_name: "ESP32 Boiler Room"

sensor:
  - platform: sht3xd
    temperature:
      name: "Boiler Room Temperature"
      id: boiler_temp
    humidity:
      name: "Boiler Room Humidity"
      id: boiler_humidity
    address: 0x44
    update_interval: 30s

switch:
  - platform: gpio
    name: "Boiler Relay 1"
    pin: GPIO23
  - platform: gpio
    name: "Boiler Relay 2"
    pin: GPIO19
  - platform: gpio
    name: "Boiler Relay 3"
    pin: GPIO18
  - platform: gpio
    name: "Boiler Relay 4"
    pin: GPIO5
  - platform: gpio
    name: "Boiler Relay 5"
    pin: GPIO17
  - platform: gpio
    name: "Boiler Relay 6"
    pin: GPIO16
  - platform: gpio
    name: "Boiler Relay 7"
    pin: GPIO4
  - platform: gpio
    name: "Boiler Relay 8"
    pin: GPIO15
```

#### Implementation Priority: **HIGH**
- **Timeline**: Immediate (hardware available)
- **Complexity**: Low/Medium (standard sensors, relay wiring)
- **Dependencies**: None

---

## Implementation Guidelines

### Sensor Selection Criteria

#### Distance Sensors for mm Accuracy
For your front entry requirement of "mm accuracy":

1. **JSN-SR04T Waterproof** (Recommended)
   - Range: 25cm - 450cm
   - Accuracy: ±1mm (under ideal conditions)
   - Waterproof design suitable for outdoor use
   - Uses standard HC-SR04 interface

2. **A02YYUW UART Distance Sensor** (Alternative)
   - Range: 30cm - 450cm  
   - Accuracy: ±1mm
   - UART interface (more reliable than GPIO timing)
   - Better temperature compensation

3. **VL53L1X ToF Laser** (Precision Option)
   - Range: Up to 400cm
   - Accuracy: ±3mm (but very precise/consistent)
   - I2C interface
   - Works well indoors, limited outdoor performance

#### Environmental Sensor Standards

Following existing node01 patterns:
- **Temperature/Humidity**: SHT30/SHT40 (I2C, proven reliable)
- **Pressure**: BMP280/BMP390 (weather-grade accuracy)
- **Light**: BH1750 digital sensor (better than analog photodiodes)

### Development Process

1. **Planning Phase**
   - Review sensor datasheets and compatibility
   - Design pin assignments and power requirements
   - Order components and test sensors individually

2. **Prototyping Phase**
   - Build breadboard prototype with all sensors
   - Test sensor accuracy and reliability
   - Validate I2C addresses and pin conflicts

3. **Configuration Phase**
   - Create ESPHome YAML configuration
   - Test individual sensor components
   - Implement sensor fusion and calculated values

4. **Deployment Phase**
   - Install in weatherproof enclosure
   - Configure Home Assistant integration
   - Set up monitoring and alerting

### Standard Configuration Patterns

#### I2C Sensor Cluster (Standard)
```yaml
i2c:
  sda: GPIO21
  scl: GPIO22
  scan: true

sensor:
  - platform: sht3xd
    temperature:
      name: "${friendly_name} Temperature"
    humidity:  
      name: "${friendly_name} Humidity"
    address: 0x44
    
  - platform: bmp280_i2c
    temperature:
      name: "${friendly_name} BMP Temperature" 
    pressure:
      name: "${friendly_name} Pressure"
    address: 0x76
```

#### High-Accuracy Distance Measurement
```yaml
# Option 1: Standard ultrasonic
sensor:
  - platform: ultrasonic
    trigger_pin: GPIO14
    echo_pin: GPIO13
    name: "${friendly_name} Distance"
    update_interval: 1s
    timeout: 3m
    filters:
      - filter_nan
      - median:
          window_size: 5
          send_every: 3

# Option 2: UART-based (higher accuracy)
uart:
  - id: distance_uart
    tx_pin: GPIO17
    rx_pin: GPIO16
    baud_rate: 9600

sensor:
  - platform: a02yyuw
    uart_id: distance_uart
    name: "${friendly_name} Distance"
```

## Resource Requirements

### Hardware Budget (Per Device)
- ESP32 DevKit: ~$8
- SHT30 sensor: ~$5
- BMP280 sensor: ~$3
- BH1750 light sensor: ~$2
- JSN-SR04T ultrasonic: ~$8
- PIR sensor: ~$3
- Breadboard/connectors: ~$5
- **Total per device**: ~$34

### Development Time Estimate
- **ESP32 Apollo (Front Entry)**: 2-3 days
  - Day 1: Component testing and pin assignment
  - Day 2: Configuration and sensor integration
  - Day 3: Installation and Home Assistant setup

## Next Steps

### Immediate Actions for ESP32 Apollo

1. **Component Sourcing**
   - [ ] Order JSN-SR04T waterproof ultrasonic sensor
   - [ ] Order SHT30 and BMP280 if not in stock
   - [ ] Order BH1750 digital light sensor
   - [ ] Prepare ESP32 development board

2. **Prototype Development**
   - [ ] Create breadboard prototype
   - [ ] Test ultrasonic sensor accuracy at various distances
   - [ ] Validate I2C sensor compatibility

3. **Configuration Creation**
   - [ ] Create `esp32-apollo.yaml` configuration
   - [ ] Test individual sensor components
   - [ ] Implement distance measurement filtering

4. **Documentation**
   - [ ] Create `ESP32-Apollo-Setup.md` documentation
   - [ ] Document pin assignments and sensor specifications

## MCP Integration Prompts

### Quick Device Creation
```
Using the ESP32-Device-Proposals.md, help me implement the ESP32 Apollo front entry device. Create the configuration file with all specified sensors and generate the setup documentation.
```

### Sensor Accuracy Testing
```
Help me test the JSN-SR04T ultrasonic sensor for mm-level accuracy. Create a test configuration that measures distance stability and implements appropriate filtering for consistent readings.
```

### Home Assistant Integration  
```
Create Home Assistant dashboards and automations for the ESP32 Apollo front entry device, including environmental monitoring and door distance alerts.
```

---

**Document Status**: Draft  
**Last Updated**: {{ current_date }}  
**Next Review**: 30 days  
**Maintainer**: TermiteTowers Project

**Priority Legend**:
⭐ **Priority** - Next device to implement
🔄 **Planning** - In design phase  
📝 **Proposed** - Concept stage